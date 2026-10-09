"""Local accounts, scrypt password hashing, expiring HttpOnly sessions."""
import hashlib, secrets, time, threading
from fastapi import HTTPException, Request
from sqlalchemy import select, func
from .db import DB, User
TOKENS = {}
ATTEMPTS = {}
LOCK = threading.Lock()

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'

def verify(password, encoded):
    return secrets.compare_digest(password_hash(password, encoded.split(':')[0]), encoded)

def needs_setup():
    with DB() as db: return db.scalar(select(func.count()).select_from(User)) == 0

def authenticate_token(token):
    with LOCK:
        item = TOKENS.get(token)
        if not item or item['expires'] < time.time():
            TOKENS.pop(token, None)
            return None
        return {k:v for k,v in item.items() if k != 'expires'}

def current_user(request: Request):
    user = authenticate_token(request.cookies.get('spatial_session'))
    if not user: raise HTTPException(401, 'Sign in to continue.')
    return user

def operator(request: Request):
    user = current_user(request)
    if user['role'] != 'operator': raise HTTPException(403, 'Operator access required.')
    return user
