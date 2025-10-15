from fastapi import FastAPI,Depends,HTTPException ,Response,Cookie
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from pydantic  import ValidationError,ConfigDict
from typing import List


from jwt_token import create_access_token,verify_token
import uvicorn
from db import *
from cryp import *




app=FastAPI()

     

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gestion-projet-front.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    
)


# Classe personnalisée pour gérer les erreurs globalement
class ErrorHandlingRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()
        async def custom_handler(request: Request) :
            try:
                return await original_handler(request)
            except HTTPException :
                raise
            except ValidationError as ve:
                        # Gérer les erreurs de validation de Pydantic
                errors=list()
                for err in ve.errors():
                    print(err)
                    errors.append( err['msg'][12:])
                
                print(errors)
                raise HTTPException(status_code=500, detail=errors)  # Lever une HTTPException 500
            except Exception as exc:
                print(exc)
                # Gérer les autres erreurs générales et lever une HTTPException 500
                raise HTTPException(status_code=500, detail=str(exc))  # Lever une HTTPException 500

        return custom_handler


app.router.route_class = ErrorHandlingRoute




class LoginModel(SQLModel):
    email : str
    psw : str
    
@app.post('/login')
async def login(identifiant:LoginModel ,response:Response, session : Session = Depends(get_session) ):

    u = session.exec(select(Users).where(Users.email == identifiant.email)).first()
    token=create_access_token(u.id)
    if u and check_psw(identifiant.psw,u.psw):
         cookie = (
        f"access_token={token}; "
        f"Max-Age=3600; "
        f"Secure; "
        f"SameSite=None; "
        f"Partitioned; "
        f"Path=/; "
        f"HttpOnly")
        response.headers.append("Set-Cookie", cookie)
        return UserBase.model_validate(u)

    
    else :
        raise HTTPException(status_code=404 , detail='identifiants incorrects')
   
        
         



class Signin(SQLModel):
    nom:str
    prenom :str
    email:str
    psw:str|bytes

@app.post('/user')
async def addUser(sign : Signin , session : Session = Depends(get_session)):

    sign.psw=generate_psw(sign.psw)
    user=Users().sqlmodel_update(sign.model_dump())
    user = Users.model_validate(user)
    session.add(user)
    session.commit()

    return "Utilisateur ajouté avec succes"


    
@app.post('/project')
async def addProject(p:Projects , session : Session = Depends(get_session) , id_user : int=Depends(verify_token)):
   
    u=session.get(Users,id_user)
    p=Projects.model_validate(p)
    p.creator=u
    session.add(p)
    session.commit()

    return 'Projet ajouté avec succes'

    
@app.patch('/project')
async def editProject(p:Projects , session : Session = Depends(get_session) , id_user :int=Depends(verify_token)):
    
    p=Projects.model_validate(p)
    old_p=session.get(Projects,p.id)
    old_p.sqlmodel_update(p.model_dump(mode='python',exclude=['id']))   
    session.add(old_p)
    session.commit()

   
    return "Projet Modifier avec success"

class ProjectTeamResponse(SQLModel):
    id : int|None = Field(default=None , primary_key=True)
    nom:str
    description:str
    statut:str
    priorite:str
    date_debut:date
    date_fin:date
    team : list['Users'] 


@app.get('/project/{id_project}')
async def getProject(id_project : int ,session : Session=Depends(get_session),id_user :str=Depends(verify_token)):
    p=session.get(Projects,id_project)
    my_team=[u.model_dump(exclude='psw',mode='python') for u in p.team]
    p=p.model_dump(mode='python')
    p['team']=my_team
    return p

   
@app.get('/projects')
async def getAllPojects(session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    
    user=session.get(Users,id_user)
    user.projects.extend(user.projects_creator)
    return user.projects


@app.delete('/project/{id_project}')
async def deleteProject(id_project:int ,session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    
    p=session.get(Projects,id_project)
    session.delete(p)
    session.commit()
    
    return "Projet Effacé avec succés"


class UsersPost(SQLModel):
    id:int |None
    nom:str |None
    prenom:str |None
    email:str |None
    date_inscription : date  |None
    poste:str |None


class Teams(SQLModel):
    creator:UsersPost|None
    team:list['UsersPost']
    reste:list['UsersPost']
    project:Projects


@app.get('/team/{id_project}')
async def getTeams(id_project:int ,session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    all_users=session.exec(select(Users)).all()
    p=session.get(Projects,id_project)
    id_creator=p.creator.id
    team=[]
    reste=[]

    creator=UsersPost(**p.creator.model_dump(include=['id','nom','prenom','email','date_inscription']),poste=None)
    for u in all_users:
        if u in p.team and u.id!=id_creator:
            team.append(UsersPost(**u.model_dump(include=['id','nom','prenom','email','date_inscription']),poste=u.get_poste(session,id_project)))
        elif(u.id !=id_creator):
            reste.append(UsersPost(**u.model_dump(include=['id','nom','prenom','email','date_inscription']),poste='Aucun'))

    
    
    return Teams(creator=creator,team=team,reste=reste,project=p)


class delete_Team(SQLModel):
    id_project : int
    id_user:int



@app.post('/delete_team')
async def delete_team(user_team:delete_Team ,session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    u=session.get(Users,user_team.id_user)
    p=session.get(Projects,user_team.id_project)
    p.team.remove(u)
    session.add(p)
    session.commit()

    return f'{u.nom} {u.prenom } supprimé du project avec succées'





@app.get('/project_tasks/{id_project}')
async def tasks(id_project : int , session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    p :Projects=session.get(Projects,id_project)
    tasks_send=[]
    for t in p.tasks:
        user=t.user
        if user :
            user=user.model_dump(exclude='psw')
        else:
            user=None
        t=t.model_dump()
        t['user']=user
        tasks_send.append(t)
    

    return  tasks_send
    





@app.post('/task')
async def add_task ( t:Tasks,session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    
    t=Tasks.model_validate(t)
    t.project=session.get(Projects,t.id_project)
    session.add(t)
    session.commit()
    return 'Tache Ajouté avec success'   

@app.delete('/task/{id_task}')
async def delete_task(id_task:int,session:Session =Depends (get_session),id_user:str=Depends(verify_token)):
    t=session.get(Tasks,id_task)
    session.delete(t)
    session.commit()
    return 'Tache effacée avec success'

@app.patch('/task')
async def edit_task ( t:Tasks,session: Session=Depends(get_session),id_user :str=Depends(verify_token)):
    old_t=session.get(Tasks,t.id)
    t=Tasks.model_validate(t)
    old_t.sqlmodel_update(t.model_dump(exclude=['id'],mode='python'))
    session.add(old_t)
    session.commit()
    return 'Taches modifié avec succées'
    
class NewPoste(SQLModel):
    id_user:int
    id_project:int
    poste:str

@app.patch('/task/user/{task_id}/{user_id}')
async def edit_task_user(task_id:int , user_id:int , session: Session=Depends(get_session),id_user :str=Depends(verify_token))  :
    t=session.get(Tasks,task_id)
    u=session.get(Users,user_id)
    if u:
        t.user=u
    else:
        t.user=None
    
    session.add(t)

    session.commit()



@app.patch('/update_poste')
async def update_poste(new_post:NewPoste,session:Session=Depends(get_session),id_user :str=Depends(verify_token)):
    p=session.get(Projects,new_post.id_project)
    u=session.get(Users,new_post.id_user)
    u.set_poste(session=session,id_project=p.id,poste=new_post.poste)
    session.add(u)
    session.commit()

    return "Changement d'habilitation effecuté avec succées"




@app.patch('/update_team/{id_project}')
async def update_team(id_project:int,team:List['int'],session:Session=Depends(get_session),id_user :str=Depends(verify_token)):

    p=session.get(Projects,id_project)
    new_member=[session.get(Users,id)  for id in team]
    p.team.extend(new_member)
    session.add(p)
    session.commit()
    
    return 'Mofication effectué avec succes'


class UserBase(SQLModel):
    id:int
    nom:str
    prenom:str
    email:str

class CommentsWithUser(SQLModel):
    txt:str
    date_comment:datetime
    user: UserBase

   

@app.get('/comments/{id_task}')
async def comments_get(id_task:int,session:Session=Depends(get_session),id_user :str=Depends(verify_token)):
    q=session.exec(select(Comments).where(Comments.id_task==id_task)).all()
    return [CommentsWithUser.model_validate(comment) for comment in q]


@app.post('/comments')
async def comments(c:Comments,session:Session=Depends(get_session),id_user :str=Depends(verify_token)):
    c.id_user =int(id_user)
    session.add(c)
    session.commit()
    




