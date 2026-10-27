import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .database import get_db
from .models import Role, User

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'development-only-change-this-secret')
ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login', auto_error=False)

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode({'sub': user.id, 'role': user.role, 'exp': expires}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request, token: Annotated[str | None, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)], x_demo_user: Annotated[str | None, Header()] = None) -> User:
    token = token or request.cookies.get('mindner_access_token')
    if not token and os.getenv('ENVIRONMENT', 'development') == 'development':
        x_demo_user = x_demo_user or 'caregiver-demo'
        demo = db.query(User).filter(User.email == ('caregiver@mindner.local' if x_demo_user == 'caregiver-demo' else 'maya@mindner.local')).first()
        if demo:
            return demo
        raise HTTPException(status_code=401, detail='Invalid demo session')
    if not token:
        raise HTTPException(status_code=401, detail='Authentication required', headers={'WWW-Authenticate':'Bearer'})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get('sub')
        if not user_id: raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired token', headers={'WWW-Authenticate':'Bearer'})
    user = db.get(User, user_id)
    if not user or not user.is_active: raise HTTPException(status_code=401, detail='User is not active')
    return user

def require_roles(*roles: Role):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in [role.value for role in roles]: raise HTTPException(status_code=403, detail='Insufficient role permissions')
        return user
    return dependency
