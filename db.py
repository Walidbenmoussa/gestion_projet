from sqlmodel import SQLModel, Field,Session,Relationship , create_engine , select ,update,col,select
from sqlalchemy.orm import selectinload,relationship

from datetime import date,datetime,timezone
from pydantic import EmailStr,model_validator,field_validator
from zoneinfo import ZoneInfo
import re

class UsersProjectsLink(SQLModel,table=True):
    id_user : int |None = Field(primary_key=True , foreign_key='users.id',default=None)
    id_project : int |None =Field(primary_key=True , foreign_key='projects.id',default=None)
    poste : str |None = Field(default='Aucun') #Admin , Chef de projet , Developpeur , Membre , Aucun


  
class Users(SQLModel,table=True):
    id:int|None=Field(default=None,primary_key=True)
    nom:str
    prenom:str
    email:str=Field(unique=True)
    date_inscription : date = Field(default=date.today())
    psw:bytes


    tasks: list['Tasks']=Relationship(back_populates='user')

    projects_creator : list['Projects'] = Relationship(back_populates='creator')
    
    projects : list['Projects'] = Relationship(back_populates='team',link_model=UsersProjectsLink)

    comments : list['Comments']=Relationship(back_populates='user')
     
    def get_poste(self,session:Session,id_project:int):
        return session.get(UsersProjectsLink,(self.id,id_project)).poste
    
    def set_poste(self,session:Session,id_project:int,poste:str):
        u_p_link=session.get(UsersProjectsLink,(self.id,id_project))
        u_p_link.poste=poste
        session.add(u_p_link)
        session.commit()
    
    @field_validator('nom')
    def validate_nom(cls, value):
        if value == '':
            raise ValueError('Merci de renseigner votre nom')
        return value

    @field_validator('prenom')
    def validate_prenom(cls, value):
        if value == '':
            raise ValueError('Merci de renseigner votre prenom')
        
        return value

    @field_validator('email')
    def validate_email(cls, value):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            raise ValueError('Adresse mail erronée')
        return value.lower()
    
    
   



class Projects(SQLModel,table=True):
    id : int|None = Field(default=None , primary_key=True)
    nom:str
    description:str
    statut:str
    priorite:str
    date_debut:date
    date_fin:date

    tasks:list['Tasks'] = Relationship(back_populates='project',sa_relationship=relationship(cascade='all, delete-orphan'))

    id_creator : int |None = Field(foreign_key='users.id', default=None)
    creator : Users = Relationship(back_populates='projects_creator')

    team : list['Users'] = Relationship(back_populates='projects' , link_model=UsersProjectsLink)

    @field_validator('statut')
    def validation_staut (cls,v):
        if (len(v)>1):
            return v
        else:
            raise ValueError('Statut vide ')
    
    @field_validator('date_debut')
    def validation_date_debut(cls,v):
        if(isinstance(v,str)):
            print('okkkkkkk')
            return date.fromisoformat(v)
        
        else:
            return v
   
    @field_validator('date_fin')
    def validation_date_fin(cls,v):
        if(isinstance(v,str)):
            print('okkkkkkk')

            return date.fromisoformat(v)
        
        else:
            return v

class Tasks(SQLModel,table=True):
    id:int|None=Field(default=None,primary_key=True)
    nom:str
    descriptif:str
    statut:str
    priorite:str
    date_debut:date
    date_fin:date


    user_id : int|None=Field(foreign_key='users.id')
    user: Users|None=Relationship(back_populates='tasks')
    
    id_project : int |None =Field(foreign_key='projects.id',default=None)
    project:Projects = Relationship(back_populates='tasks')
    
    comments:list['Comments']=Relationship(back_populates='task')




class Comments(SQLModel,table=True):
    id:int|None =Field(default=None,primary_key=True)
    txt:str
    date_comment:datetime=Field(default=datetime.now(ZoneInfo('Europe/Paris')))

    id_task : int |None = Field(foreign_key='tasks.id', default=None)
    task : Tasks = Relationship(back_populates='comments')

    id_user:int |None=Field(foreign_key='users.id',default=None)
    user: Users=Relationship(back_populates='comments')



#engine = create_engine(url='sqlite:////home/walid/GestionProjet/sqlapi/base.db')
engine = create_engine(
    'mysql+pymysql://413433:cc131415*@mysql-my-site-db-13.alwaysdata.net/my-site-db-13_gestion_projet'
)
SQLModel.metadata.create_all(engine)



def get_session():
    with Session(engine,autoflush=False) as session:
        yield session
