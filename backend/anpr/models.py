from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from backend.database import Base


class Camera(Base):
    """
    SQLAlchemy ORM model for `cameras` table.
    Represents physical CCTV / ANPR camera locations in the city.
    """
    __tablename__ = "cameras"

    camera_id = Column(String(20), primary_key=True)
    gps_lat = Column(Float, nullable=False)
    gps_lng = Column(Float, nullable=False)
    location_name = Column(String(100), nullable=True)

    # Relationships
    sightings = relationship("Sighting", back_populates="camera", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Camera(camera_id='{self.camera_id}', location='{self.location_name}')>"


class Sighting(Base):
    """
    SQLAlchemy ORM model for `sightings` table.
    Represents an ANPR vehicle plate detection event.
    """
    __tablename__ = "sightings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_text = Column(String(15), nullable=False, index=True)
    camera_id = Column(String(20), ForeignKey("cameras.camera_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    gps_lat = Column(Float, nullable=False)
    gps_lng = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    vehicle_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    camera = relationship("Camera", back_populates="sightings")

    # Composite index for camera_id + timestamp queries
    __table_args__ = (
        Index("idx_sightings_camera_time", "camera_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<Sighting(id={self.id}, plate='{self.plate_text}', "
            f"camera='{self.camera_id}', time='{self.timestamp}', conf={self.confidence:.2f})>"
        )
