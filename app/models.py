from datetime import date, datetime, timezone
from enum import Enum
from uuid import uuid4
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Role(str, Enum):
    patient = 'PATIENT'
    caregiver = 'CAREGIVER'
    admin = 'ADMIN'
    healthcare_worker = 'HEALTHCARE_WORKER'

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    patient: Mapped['Patient | None'] = relationship(back_populates='user', uselist=False)

class Patient(Base):
    __tablename__ = 'patients'
    id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), primary_key=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default='en')
    region: Mapped[str | None] = mapped_column(String(120))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    user: Mapped[User] = relationship(back_populates='patient')

class CaregiverPatientAssignment(Base):
    __tablename__ = 'caregiver_patient_assignments'
    caregiver_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey('patients.id'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Game(Base):
    __tablename__ = 'games'
    game_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))

class GameSession(Base):
    __tablename__ = 'game_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey('patients.id'), index=True)
    game_type: Mapped[str] = mapped_column(String(50), ForeignKey('games.game_type'))
    difficulty_level: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

class GameResult(Base):
    __tablename__ = 'game_results'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey('game_sessions.id'), unique=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    score: Mapped[int] = mapped_column(Integer)
    accuracy: Mapped[float] = mapped_column(Float)
    response_time: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer)
    mistakes: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean)
    cps: Mapped[float | None] = mapped_column(Float)
    accuracy_component: Mapped[float | None] = mapped_column(Float)
    reaction_component: Mapped[float | None] = mapped_column(Float)
    completion_component: Mapped[float | None] = mapped_column(Float)
    consistency_component: Mapped[float | None] = mapped_column(Float)
    recommended_difficulty: Mapped[int | None] = mapped_column(Integer)
    recommended_activity: Mapped[str | None] = mapped_column(String(50))
    recommendation_model: Mapped[str | None] = mapped_column(String(40))
    recommendation_explanation: Mapped[str | None] = mapped_column(Text)
    caregiver_notification: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class Reminder(Base):
    __tablename__ = 'reminders'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey('patients.id'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    reminder_type: Mapped[str] = mapped_column(String(40))
    reminder_time: Mapped[str] = mapped_column(String(5))
    recurrence: Mapped[str] = mapped_column(String(20), default='DAILY')
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    end_date: Mapped[date | None] = mapped_column(Date)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey('patients.id'), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='new')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class DailyAggregate(Base):
    __tablename__ = 'daily_aggregates'
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey('patients.id'), primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sessions_completed: Mapped[int] = mapped_column(Integer, default=0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[float] = mapped_column(Float, default=0)
    average_accuracy: Mapped[float] = mapped_column(Float, default=0)
    average_reaction_time: Mapped[float] = mapped_column(Float, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0)

class WeeklyAggregate(Base):
    __tablename__ = 'weekly_aggregates'
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey('patients.id'), primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, primary_key=True)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[float] = mapped_column(Float, default=0)
    average_accuracy: Mapped[float] = mapped_column(Float, default=0)
    average_reaction_time: Mapped[float] = mapped_column(Float, default=0)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

Index('ix_game_session_patient_time', GameSession.patient_id, GameSession.started_at)
UniqueConstraint(GameResult.event_id, name='uq_game_results_event_id')
