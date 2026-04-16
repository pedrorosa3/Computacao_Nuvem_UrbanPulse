from sqlalchemy import Column, Integer, String, Float, Date
from .database import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    pickup_date = Column(Date, nullable=False)
    pickup_zone_id = Column(Integer, nullable=False)
    payment_type = Column(String, nullable=False)
    fare_amount = Column(Float, nullable=False)
    tip_amount = Column(Float, default=0.0)
    passenger_count = Column(Integer)