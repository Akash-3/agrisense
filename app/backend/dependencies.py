from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import execute_db
import time

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    row = execute_db(
        "SELECT farmer_id, expires_at FROM auth_sessions WHERE session_token = ?",
        (token,),
        fetchone=True
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    farmer_id, expires_at = row
    
    if time.time() > expires_at:
        execute_db("DELETE FROM auth_sessions WHERE session_token = ?", (token,), commit=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return farmer_id
