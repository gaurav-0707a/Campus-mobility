import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import User, Passenger, Ride
from auth import create_token, decode_token
from constants import ZONES

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

def get_pass(request, db):
    tok = request.cookies.get("token")
    if not tok:
        return None
    info = decode_token(tok)
    if not info or info.get("role") != "passenger":
        return None
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
    return p

@router.get("/customer/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="customer/login.html")

@router.post("/customer/login")
async def login_submit(request: Request, name: str = Form(...), phone: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.phone == phone).first()
    if not u:
        u = User(name=name, phone=phone, password_hash="", role="passenger")
        db.add(u)
        db.flush()
        db.add(Passenger(user_id=u.id))
        db.commit()
        db.refresh(u)
    else:
        p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
        if not p:
            db.add(Passenger(user_id=u.id))
            db.commit()
    tok = create_token(u.id, u.role)
    res = RedirectResponse(url="/customer/home", status_code=302)
    res.set_cookie(key="token", value=tok, httponly=True)
    return res

@router.get("/customer/home", response_class=HTMLResponse)
async def home_page(request: Request, db: Session = Depends(get_db)):
    tok = request.cookies.get("token")
    if not tok:
        return RedirectResponse(url="/customer/login", status_code=302)
    info = decode_token(tok)
    if not info:
        return RedirectResponse(url="/customer/login", status_code=302)
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    from sqlalchemy import func
    from models import Driver
    avail = db.query(Driver.current_zone, func.count(Driver.id).label("cnt")).filter(
        Driver.is_online == True, Driver.is_available == True
    ).group_by(Driver.current_zone).all()
    zcounts = {z: c for z, c in avail if z}
    return templates.TemplateResponse(request=request, name="customer/home.html",
        context={"zones": ZONES, "user_name": u.name, "zone_counts": zcounts})

@router.post("/customer/request-ride")
async def req_ride(request: Request, pickup_zone: str = Form(...), destination_zone: str = Form(...), db: Session = Depends(get_db)):
    tok = request.cookies.get("token")
    if not tok:
        return RedirectResponse(url="/customer/login", status_code=302)
    info = decode_token(tok)
    if not info:
        return RedirectResponse(url="/customer/login", status_code=302)
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
    if p.suspension_until and p.suspension_until > datetime.utcnow():
        return templates.TemplateResponse(request=request, name="customer/home.html",
            context={"zones": ZONES, "user_name": u.name, "error": "Account suspended."})
    existing = db.query(Ride).filter(
        Ride.passenger_id == p.id,
        Ride.status.in_(["pending", "assigned", "in_progress"])
    ).first()
    if existing:
        return RedirectResponse(url=f"/customer/ride/{existing.id}", status_code=302)
    from queue_service import get_next_driver
    drv = get_next_driver(pickup_zone, db)
    if not drv:
        return templates.TemplateResponse(request=request, name="customer/home.html",
            context={"zones": ZONES, "user_name": u.name, "error": f"No drivers near {pickup_zone}."})
    ride = Ride(passenger_id=p.id, driver_id=drv.id, pickup_zone=pickup_zone,
        destination_zone=destination_zone, status="assigned", assigned_at=datetime.utcnow())
    db.add(ride)
    drv.is_available = False
    db.commit()
    db.refresh(ride)
    return RedirectResponse(url=f"/customer/ride/{ride.id}", status_code=302)

@router.get("/customer/ride/{rid}", response_class=HTMLResponse)
async def ride_page(rid: int, request: Request, db: Session = Depends(get_db)):
    tok = request.cookies.get("token")
    if not tok:
        return RedirectResponse(url="/customer/login", status_code=302)
    info = decode_token(tok)
    if not info:
        return RedirectResponse(url="/customer/login", status_code=302)
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride or ride.passenger_id != p.id:
        return RedirectResponse(url="/customer/home", status_code=302)
    can_cancel = False
    if ride.assigned_at:
        elapsed = (datetime.utcnow() - ride.assigned_at).seconds
        can_cancel = elapsed < 60
    dname = ride.driver.user.name if ride.driver else None
    dphone = ride.driver.user.phone if ride.driver else None
    davg = None
    if ride.driver:
        from models import Ride as R
        rated = [r.rating for r in db.query(R).filter(R.driver_id == ride.driver.id, R.rating != None).all()]
        davg = round(sum(rated)/len(rated), 1) if rated else None
    return templates.TemplateResponse(request=request, name="customer/track.html",
        context={"ride": ride, "driver_name": dname, "driver_phone": dphone,
             "can_cancel": can_cancel, "user_name": u.name, "driver_avg": davg})


@router.post("/customer/cancel/{rid}")
async def cancel_ride(rid: int, request: Request, db: Session = Depends(get_db)):
    tok = request.cookies.get("token")
    if not tok:
        return RedirectResponse(url="/customer/login", status_code=302)
    info = decode_token(tok)
    if not info:
        return RedirectResponse(url="/customer/login", status_code=302)
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride or ride.passenger_id != p.id:
        return RedirectResponse(url="/customer/home", status_code=302)
    elapsed = (datetime.utcnow() - ride.assigned_at).seconds
    if elapsed > 60:
        return RedirectResponse(url=f"/customer/ride/{rid}", status_code=302)
    ride.status = "cancelled"
    ride.cancellation_reason = "passenger_cancel"
    if ride.driver:
        ride.driver.is_available = True
        ride.driver.queue_entry_time = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/customer/home", status_code=302)

@router.post("/customer/rate/{rid}")
async def rate_ride(rid: int, request: Request, rating: int = Form(...), feedback: str = Form(None), db: Session = Depends(get_db)):
    tok = request.cookies.get("token")
    if not tok:
        return RedirectResponse(url="/customer/login", status_code=302)
    info = decode_token(tok)
    if not info:
        return RedirectResponse(url="/customer/login", status_code=302)
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride or ride.passenger_id != p.id:
        return RedirectResponse(url="/customer/home", status_code=302)
    ride.rating = rating
    ride.feedback_text = feedback
    db.commit()
    return RedirectResponse(url="/customer/home", status_code=302)

@router.get("/customer/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    tok = request.cookies.get("token")
    if not tok:
        return RedirectResponse(url="/customer/login", status_code=302)
    info = decode_token(tok)
    if not info:
        return RedirectResponse(url="/customer/login", status_code=302)
    u = db.query(User).filter(User.id == int(info["sub"])).first()
    p = db.query(Passenger).filter(Passenger.user_id == u.id).first()
    done = db.query(Ride).filter(Ride.passenger_id == p.id, Ride.status == "completed").count()
    cancelled = db.query(Ride).filter(Ride.passenger_id == p.id, Ride.status == "cancelled").count()
    return templates.TemplateResponse(request=request, name="customer/profile.html",
        context={"user_name": u.name, "user_phone": u.phone, "cancel_flags": p.cancel_flags,
                 "suspension_until": p.suspension_until, "total_done": done, "total_cancelled": cancelled})