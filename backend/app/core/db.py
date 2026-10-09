"""SQLAlchemy schema shared by SQLite and PostgreSQL."""
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Float, Integer, JSON, ForeignKey, Text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATA

def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default='operator')
class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    source: Mapped[str] = mapped_column(String(120))
    started: Mapped[str] = mapped_column(String(40), default=now)
    ended: Mapped[str | None] = mapped_column(String(40), nullable=True)
    settings: Mapped[dict] = mapped_column(JSON)
class Frame(Base):
    __tablename__ = 'frames'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    seq: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[float] = mapped_column(Float)
    image: Mapped[str] = mapped_column(Text)
    state: Mapped[dict] = mapped_column(JSON)
class Track(Base):
    __tablename__ = 'tracks'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    track_id: Mapped[str] = mapped_column(String(24))
    state: Mapped[dict] = mapped_column(JSON)
class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    timestamp: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text)
    related_track_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
# Sample tables deliberately use JSON payloads so future sensor schemas can evolve.
class SampleMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
class TrackPoint(SampleMixin, Base): __tablename__ = 'track_points'
class Detection(SampleMixin, Base): __tablename__ = 'detections'
class Scene(SampleMixin, Base): __tablename__ = 'scenes'
class Waypoint(SampleMixin, Base): __tablename__ = 'waypoints'
class SensorStatus(SampleMixin, Base): __tablename__ = 'sensor_status'
class SystemMetric(SampleMixin, Base): __tablename__ = 'system_metrics'

url = os.getenv('DATABASE_URL', 'sqlite:///' + str(DATA / 'spatiallens.db'))
engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 15} if url.startswith('sqlite') else {}, pool_pre_ping=True)
if url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA foreign_keys=ON')
DB = sessionmaker(engine, expire_on_commit=False)
