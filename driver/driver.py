import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import User, Driver, Ride
from constants import ZONES

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

def get_drv(request, db):
    from auth import decode_token
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

@router.get("/driver/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="driver/login.html")

@router.post("/driver/login")
async def login_submit(request: Request, phone: str = Form(...), pin: str = Form(...), db: Session = Depends(get_db)):
    import bcrypt
    from auth import create_token
    u = db.query(User).filter(User.phone == phone, User.role == "driver").first()
    if not u:
        return templates.TemplateResponse(request=request, name="driver/login.html",
            context={"error": "Phone not found"})
    if not bcrypt.checkpw(pin.encode('utf-8'), u.password_hash.encode('utf-8')):
        return templates.TemplateResponse(request=request, name="driver/login.html",
            context={"error": "Wrong PIN"})
    tok = create_token(u.id, u.role)
    res = RedirectResponse(url="/driver/home", status_code=302)
    res.set_cookie(key="driver_token", value=tok, httponly=True)
    return res

@router.get("/driver/home", response_class=HTMLResponse)
async def drv_home(request: Request, db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    active = db.query(Ride).filter(Ride.driver_id == d.id, Ride.status.in_(["assigned", "in_progress"])).first()
    if active and active.status == "assigned":
        pname = active.passenger.user.name
        return templates.TemplateResponse(request=request, name="driver/incoming_rides.html",
            context={"driver_name": u.name, "ride": active, "passenger_name": pname})
    if active and active.status == "in_progress":
        pname = active.passenger.user.name
        return templates.TemplateResponse(request=request, name="driver/ride_progress.html",
            context={"driver_name": u.name, "ride": active, "passenger_name": pname})
    from sqlalchemy import desc
    history = db.query(Ride).filter(Ride.driver_id == d.id, Ride.status.in_(["completed", "cancelled"])).order_by(desc(Ride.requested_at)).all()
    rated = [r.rating for r in history if r.rating is not None]
    avg = round(sum(rated)/len(rated), 1) if rated else "No ratings yet"
    ctx = {"driver_name": u.name, "ride_count": d.ride_count, "penalty_seconds": d.penalty_seconds,
           "zones": ZONES, "ride_history": history, "avg_rating": avg, "total_ratings": len(rated)}
    if d.is_online:
        ctx["current_zone"] = d.current_zone
        return templates.TemplateResponse(request=request, name="driver/home_online.html", context=ctx)
    return templates.TemplateResponse(request=request, name="driver/home_offline.html", context=ctx)

@router.post("/driver/online")
async def go_online(request: Request, zone: str = Form(...), db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    d.is_online = True
    d.is_available = True
    d.current_zone = zone
    d.queue_entry_time = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)

@router.post("/driver/offline")
async def go_offline(request: Request, db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    d.is_online = False
    d.is_available = False
    d.current_zone = None
    d.queue_entry_time = None
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)

@router.post("/driver/zone")
async def chg_zone(request: Request, new_zone: str = Form(...), db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    d.current_zone = new_zone
    d.queue_entry_time = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)

@router.post("/driver/accept/{rid}")
async def accept_ride(rid: int, request: Request, db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride:
        return RedirectResponse(url="/driver/home", status_code=302)
    ride.status = "in_progress"
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)
@router.post("/driver/reject/{rid}")
async def reject_ride(rid: int, request: Request, db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride:
        return RedirectResponse(url="/driver/home", status_code=302)
    ride.driver_id = None
    ride.assigned_at = None
    d.is_available = True
    d.queue_entry_time = datetime.utcnow()
    db.commit()
    from queue_service import get_next_driver
    next_drv = get_next_driver(ride.pickup_zone, db)
    if next_drv:
        ride.status = "assigned"
        ride.driver_id = next_drv.id
        ride.assigned_at = datetime.utcnow()
        next_drv.is_available = False
    else:
        ride.status = "cancelled"
        ride.cancellation_reason = "no_drivers"
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)

@router.post("/driver/complete/{rid}")
async def complete_ride(rid: int, request: Request, db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride:
        return RedirectResponse(url="/driver/home", status_code=302)
    ride.status = "completed"
    ride.completed_at = datetime.utcnow()
    d.ride_count += 1
    d.is_available = True
    d.queue_entry_time = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)

@router.post("/driver/cancel/{rid}")
async def cancel_ride(rid: int, request: Request, db: Session = Depends(get_db)):
    u, d = get_drv(request, db)
    if not d:
        return RedirectResponse(url="/driver/login", status_code=302)
    ride = db.query(Ride).filter(Ride.id == rid).first()
    if not ride:
        return RedirectResponse(url="/driver/home", status_code=302)
    from constants import PENALTY
    ride.status = "cancelled"
    ride.cancellation_reason = "driver_cancel"
    d.penalty_seconds += PENALTY
    d.is_available = True
    d.queue_entry_time = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/driver/home", status_code=302)

@router.get("/driver/logout")
async def logout(request: Request):
    res = RedirectResponse(url="/driver/login", status_code=302)
    res.delete_cookie(key="driver_token")
    return res