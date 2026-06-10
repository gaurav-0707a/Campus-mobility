from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_online = Column(Boolean, default=False)
    is_available = Column(Boolean, default=False)
    current_zone = Column(String, nullable=True)
    queue_entry_time = Column(DateTime, nullable=True)
    penalty_seconds = Column(Integer, default=0)
    ride_count = Column(Integer, default=0)
    no_show_strikes = Column(Integer, default=0)
    vehicle_info = Column(String, nullable=True)
    verification_info = Column(String, nullable=True)
    user = relationship("User")
class Passenger(Base):
    __tablename__ = "passengers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cancel_flags = Column(Integer, default=0)
    suspension_until = Column(DateTime, nullable=True)
    user = relationship("User")
class Ride(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True, index=True)
    passenger_id = Column(Integer, ForeignKey("passengers.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    pickup_zone = Column(String, nullable=False)
    destination_zone = Column(String, nullable=False)
    status = Column(String, default="pending")
    requested_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)
    feedback_text = Column(String, nullable=True)
    passenger = relationship("Passenger")
    driver = relationship("Driver")