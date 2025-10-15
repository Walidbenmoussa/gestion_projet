from fastapi.security import OAuth2PasswordBearer ,APIKeyCookie
from jwt import ExpiredSignatureError, InvalidTokenError
import jwt
from datetime import datetime, timedelta,timezone
from fastapi import HTTPException ,Depends,Header,Request




SECRET_KEY = "votre_cle_secrete"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60



AccessToken= APIKeyCookie(name='access_token',auto_error=False)



def create_access_token(id_user: int):

    to_encode ={"sub":str(id_user)}
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print('encoded token',encoded_jwt)
    return encoded_jwt




def verify_token(token : str=Depends(AccessToken)):
    try:
        if not token:
            raise HTTPException(status_code=401, detail="Echec d'authentification")
        else:
            payload= jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
            id_user=int(payload.get('sub'))
            
            return id_user


    
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except InvalidTokenError :
        raise HTTPException(status_code=403, detail="Token invalide")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500,detail=str(e))