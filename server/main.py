import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from models import User, Driver, Passenger, Ride
Base.metadata.create_all(bind=engine)
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/customer/login")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from customer.customer import router as customer_router
from driver.driver import router as driver_router
import auth
app.include_router(customer_router)
app.include_router(driver_router)
app.include_router(auth.router)