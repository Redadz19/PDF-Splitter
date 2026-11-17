from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class License(Base):
    __tablename__ = 'licenses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serial_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), default='pro')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    devices: Mapped[list['Device']] = relationship(back_populates='license', cascade='all, delete-orphan')

class Device(Base):
    __tablename__ = 'devices'
    __table_args__ = (UniqueConstraint('license_id', 'device_id', name='uq_license_device'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey('licenses.id', ondelete='CASCADE'), index=True)
    device_id: Mapped[str] = mapped_column(String(128))
    device_name: Mapped[str] = mapped_column(String(128), default='Windows PC')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    license: Mapped[License] = relationship(back_populates='devices')
