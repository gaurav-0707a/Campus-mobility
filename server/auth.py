from datetime import datetime, timedelta
import os
import jwt
import bcrypt
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, Driver
from constants import SECRET_KEY, ALGORITHM, TOKEN_EXPIRE_HOURS

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

def hashpw(pw):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw.encode('utf-8'), salt).decode('utf-8')

def checkpw(plain, hashed):
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def create_token(uid, role):
    exp = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    data = {"sub": str(uid), "role": role, "exp": exp}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(tok):
    try:
        return jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_driver(request: Request, db: Session):
    tok = request.cookies.get("driver_token")
    if not tok:
        return None, None
    info = decode_token(tok)
    if not info or info.get("role") != "driver":
        return None, None
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    if not u:
        return None, None
    d = db.query(Driver).filter(Driver.user_id == u.id).first()
    return u, d

@router.get("/driver/register", response_class=HTMLResponse)
async def reg_page(request: Request):
    return templates.TemplateResponse(request=request, name="driver/register.html")

@router.post("/driver/register")
async def reg_submit(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    pin: str = Form(...),
    vinfo: str = Form(...),
    verinfo: str = Form(...),
    db: Session = Depends(get_db)
):
    if len(pin) != 4 or not pin.isdigit():
        return templates.TemplateResponse(request=request, name="driver/register.html",
            context={"error": "PIN must be 4 digits"})
    if db.query(User).filter(User.phone == phone).first():
        return templates.TemplateResponse(request=request, name="driver/register.html",
            context={"error": "Phone already registered"})
    u = User(name=name, phone=phone, password_hash=hashpw(pin), role="driver")
    db.add(u)
    db.commit()
    db.refresh(u)
    d = Driver(user_id=u.id, vehicle_info=vinfo, verification_info=verinfo)
    db.add(d)
    db.commit()
    return RedirectResponse(url="/driver/login", status_code=302)