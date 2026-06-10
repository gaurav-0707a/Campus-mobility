from sqlalchemy.orm import Session
from models import Driver
from datetime import timedelta
from constants import NEARBY_ZONES
def get_next_driver(zone, db: Session):
    zones = [zone] + NEARBY_ZONES.get(zone, [])
    for z in zones:
        found = db.query(Driver).filter(
            Driver.is_online == True,
            Driver.is_available == True,
            Driver.current_zone == z
        ).all()
        if found:
            found.sort(key=lambda d: d.queue_entry_time + timedelta(seconds=d.penalty_seconds))
            return found[0]
    return None