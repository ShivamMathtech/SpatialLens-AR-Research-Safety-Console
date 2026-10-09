"""Create a viewer or reset a local account using OS access; never logs passwords."""
import argparse, getpass, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.core.db import Base,DB,engine,User
from backend.app.core.security import password_hash
p=argparse.ArgumentParser();p.add_argument('username');p.add_argument('--role',choices=['viewer','operator'],default='viewer');p.add_argument('--reset',action='store_true');args=p.parse_args()
password=getpass.getpass('New password (10+ characters): ')
if not 10<=len(password)<=128: raise SystemExit('Password must be 10–128 characters.')
if password!=getpass.getpass('Confirm password: '): raise SystemExit('Passwords differ.')
Base.metadata.create_all(engine)
with DB.begin() as db:
    user=db.get(User,args.username)
    if user and not args.reset: raise SystemExit('Account exists. Use --reset to change it.')
    if user: user.password_hash=password_hash(password);user.role=args.role
    else: db.add(User(username=args.username,password_hash=password_hash(password),role=args.role))
print('Account updated. Restart the server to revoke any previously active sessions.')
