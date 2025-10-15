from bcrypt import hashpw,gensalt,checkpw



def generate_psw(psw:str):
    psw_bytes:bytes=psw.encode()
    psw_hashed=hashpw(psw_bytes,gensalt())
    return psw_hashed

def check_psw(psw_to_verify:str,psw_hashed:bytes):
    return checkpw(psw_to_verify.encode(),psw_hashed)