from dotenv import load_dotenv
load_dotenv()
import asyncio
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from .ai.difficulty import recommend_difficulty as recommend_pattern_difficulty
from .adaptive import recommend_difficulty
from .auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from .database import Base, engine, get_db
from .models import Alert, AuditLog, CaregiverPatientAssignment, DailyAggregate, Game, GameResult, GameSession, Patient, Reminder, Role, User, WeeklyAggregate

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(_: FastAPI):
    with Session(engine) as db:
        ensure_demo(db)
    scheduler = asyncio.create_task(alert_scheduler())
    yield
    scheduler.cancel()
    await asyncio.gather(scheduler, return_exceptions=True)

app = FastAPI(title='MINDNER API', version='0.2.0', lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    if os.getenv('ENVIRONMENT') == 'production' and request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and request.cookies.get('mindner_access_token'):
        expected = request.cookies.get('mindner_csrf')
        provided = request.headers.get('X-CSRF-Token')
        if not expected or not provided or not secrets.compare_digest(expected, provided):
            return Response(content='{"detail":"CSRF validation failed"}', status_code=403, media_type='application/json')
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'microphone=(self)'
    if request.url.scheme == 'https': response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
origins = [item.strip() for item in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174').split(',')]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
DEMO_PATIENT_ID = '11111111-1111-1111-1111-111111111111'

async def alert_scheduler():
    while True:
        await asyncio.sleep(900)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            patients = db.query(Patient).all()
            for patient_record in patients:
                recent = db.query(GameResult).join(GameSession, GameSession.id == GameResult.session_id).filter(GameSession.patient_id == patient_record.id, GameResult.recorded_at >= now - timedelta(days=3)).count()
                if recent == 0 and not db.query(Alert).filter(Alert.patient_id == patient_record.id, Alert.message == 'Recent activity is lower than usual. Please review the daily routine.', Alert.created_at >= now - timedelta(days=1)).first():
                    db.add(Alert(patient_id=patient_record.id, message='Recent activity is lower than usual. Please review the daily routine.', status='new'))
            db.commit()

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: str
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.caregiver
class LoginIn(BaseModel):
    email: str = Field(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str
class PatientIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(min_length=8, max_length=128)
    preferred_language: str = Field(default='en', max_length=10)
    region: str | None = Field(default=None, max_length=120)
class ResultIn(BaseModel):
    event_id: UUID
    patient_id: UUID
    session_id: UUID | None = None
    game_type: str = Field(min_length=2, max_length=50)
    difficulty_level: int = Field(ge=1, le=3)
    score: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)
    response_time: float = Field(ge=0)
    attempts: int = Field(ge=1)
    mistakes: int = Field(default=0, ge=0)
    completed: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
class ReminderIn(BaseModel):
    patient_id: UUID
    title: str = Field(min_length=1, max_length=120)
    reminder_type: str = Field(min_length=1, max_length=40)
    time: str = Field(pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    recurrence: str = 'DAILY'
    description: str | None = None
    enabled: bool = True
class GameSessionIn(BaseModel):
    patient_id: UUID
    game_type: str
    difficulty_level: int = Field(ge=1, le=3)

Base.metadata.create_all(bind=engine)

def log(db: Session, user: User, action: str):
    db.add(AuditLog(user_id=user.id, action=action))

def ensure_demo(db: Session):
    if db.query(User).filter(User.email == 'caregiver@mindner.local').first():
        return
    caregiver = User(id='22222222-2222-2222-2222-222222222222', name='Ananya Das', email='caregiver@mindner.local', password_hash=hash_password('demo-password'), role=Role.caregiver.value)
    patient_user = User(id=DEMO_PATIENT_ID, name='Maya Das', email='maya@mindner.local', password_hash=hash_password('demo-password'), role=Role.patient.value)
    db.add_all([caregiver, patient_user])
    db.flush()
    db.add(Patient(id=DEMO_PATIENT_ID, preferred_language='en', region='North-East India'))
    db.flush()
    db.add(CaregiverPatientAssignment(caregiver_id=caregiver.id, patient_id=DEMO_PATIENT_ID))
    db.add_all([Game(game_type=kind, display_name=kind.replace('_', ' ').title()) for kind in ['MEMORY_MATCH','ATTENTION_TEST','PATTERN_RECOGNITION','DAILY_ROUTINE_RECALL']])
    db.commit()

with Session(engine) as db:
    ensure_demo(db)

def can_access(db: Session, user: User, patient_id: str):
    if user.role in (Role.admin.value, Role.healthcare_worker.value):
        return
    if user.role == Role.patient.value and user.id == patient_id:
        return
    if not db.query(CaregiverPatientAssignment).filter_by(caregiver_id=user.id, patient_id=patient_id).first():
        raise HTTPException(status_code=403, detail='Patient is not assigned to this caregiver')

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/auth/register', response_model=UserOut, status_code=201)
@limiter.limit('5/minute')
def register(request: Request, payload: RegisterIn, db: Annotated[Session, Depends(get_db)]):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail='Email already registered')
    user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password), role=payload.role.value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post('/auth/login')
@limiter.limit('10/minute')
def login(request: Request, response: Response, payload: LoginIn, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    token = create_access_token(user)
    response.set_cookie('mindner_access_token', token, httponly=True, secure=os.getenv('ENVIRONMENT') == 'production', samesite='lax', max_age=1800)
    response.set_cookie('mindner_csrf', secrets.token_urlsafe(32), httponly=False, secure=os.getenv('ENVIRONMENT') == 'production', samesite='lax', max_age=1800)
    return {'status': 'authenticated', 'token_type': 'cookie'}

@app.post('/auth/logout')
def logout(response: Response):
    response.delete_cookie('mindner_access_token')
    response.delete_cookie('mindner_csrf')
    return {'status': 'logged_out'}

@app.get('/auth/me', response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user

@app.post('/patients', response_model=UserOut, status_code=201)
def create_patient(payload: PatientIn, user: Annotated[User, Depends(require_roles(Role.caregiver, Role.admin))], db: Annotated[Session, Depends(get_db)]):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail='Email already registered')
    patient_user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password), role=Role.patient.value)
    db.add(patient_user)
    db.flush()
    db.add(Patient(id=patient_user.id, preferred_language=payload.preferred_language, region=payload.region))
    db.add(CaregiverPatientAssignment(caregiver_id=user.id, patient_id=patient_user.id))
    log(db, user, 'patient.created')
    db.commit()
    db.refresh(patient_user)
    return patient_user

@app.get('/patients/{patient_id}')
def patient(patient_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(patient_id))
    item = db.query(Patient).filter_by(id=str(patient_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail='Patient not found')
    return {'id': item.id, 'name': item.user.name, 'language': item.preferred_language, 'region': item.region}

@app.get('/patients')
def patients(user: Annotated[User, Depends(require_roles(Role.caregiver, Role.admin, Role.healthcare_worker))], db: Annotated[Session, Depends(get_db)]):
    query = db.query(Patient).join(CaregiverPatientAssignment, CaregiverPatientAssignment.patient_id == Patient.id)
    if user.role == Role.caregiver.value: query = query.filter(CaregiverPatientAssignment.caregiver_id == user.id)
    return [{'id': item.id, 'name': item.user.name, 'language': item.preferred_language, 'region': item.region} for item in query.all()]

@app.post('/game-sessions')
def create_session(payload: GameSessionIn, user: Annotated[User, Depends(require_roles(Role.patient, Role.caregiver))], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(payload.patient_id))
    session = GameSession(patient_id=str(payload.patient_id), game_type=payload.game_type, difficulty_level=payload.difficulty_level)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {'session_id': session.id, 'difficulty_level': session.difficulty_level}

def store_result(payload: ResultIn, user: User, db: Session):
    can_access(db, user, str(payload.patient_id))
    if db.query(GameResult).filter_by(event_id=str(payload.event_id)).first():
        return {'status': 'already_synced', 'event_id': str(payload.event_id)}
    pattern_decision = None
    if payload.game_type == 'PATTERN_RECOGNITION':
        historical_rows = db.query(GameResult, GameSession.difficulty_level).join(
            GameSession, GameSession.id == GameResult.session_id
        ).filter(
            GameSession.patient_id == str(payload.patient_id),
            GameSession.game_type == payload.game_type,
            GameResult.completed.is_(True),
        ).order_by(GameResult.recorded_at.desc()).limit(100).all()
        history = [
            {
                'accuracy': row.accuracy,
                'response_time': row.response_time,
                'attempts': row.attempts,
                'completed': row.completed,
                'score': row.score,
                'difficulty_level': difficulty,
            }
            for row, difficulty in reversed(historical_rows)
        ]
        pattern_decision = recommend_pattern_difficulty(
            current_accuracy=payload.accuracy,
            current_response_time=payload.response_time,
            current_score=payload.score,
            current_attempts=payload.attempts,
            current_completed=payload.completed,
            previous_difficulty=payload.difficulty_level,
            history=history,
        )
    session_id = str(payload.session_id) if payload.session_id else None
    if not session_id:
        session = GameSession(patient_id=str(payload.patient_id), game_type=payload.game_type, difficulty_level=payload.difficulty_level, completed_at=payload.timestamp)
        db.add(session)
        db.flush()
        session_id = session.id
    result = GameResult(
        session_id=session_id,
        event_id=str(payload.event_id),
        score=payload.score,
        accuracy=payload.accuracy,
        response_time=payload.response_time,
        attempts=payload.attempts,
        mistakes=payload.mistakes,
        completed=payload.completed,
        cps=pattern_decision.cps if pattern_decision else None,
        accuracy_component=pattern_decision.components['accuracy'] if pattern_decision else None,
        reaction_component=pattern_decision.components['reaction'] if pattern_decision else None,
        completion_component=pattern_decision.components['completion'] if pattern_decision else None,
        consistency_component=pattern_decision.components['consistency'] if pattern_decision else None,
        recommended_difficulty=pattern_decision.next_difficulty if pattern_decision else None,
        recommended_activity=pattern_decision.next_activity if pattern_decision else None,
        recommendation_model=pattern_decision.model_used if pattern_decision else None,
        recommendation_explanation=pattern_decision.explanation if pattern_decision else None,
        caregiver_notification=pattern_decision.caregiver_notification if pattern_decision else False,
        recorded_at=payload.timestamp,
    )
    db.add(result)
    if pattern_decision and pattern_decision.caregiver_notification:
        db.add(Alert(
            patient_id=str(payload.patient_id),
            message='Pattern-game CPS was below 40. An easier activity is recommended; please review the recent session.',
            status='new',
        ))
    if payload.completed and payload.accuracy < .60 and not (pattern_decision and pattern_decision.caregiver_notification):
        db.add(Alert(patient_id=str(payload.patient_id), message='Recent game performance is lower than usual. Please review recent activity.', status='new'))
    if payload.completed:
        stat_date = payload.timestamp.date()
        aggregate = db.query(DailyAggregate).filter_by(patient_id=str(payload.patient_id), stat_date=stat_date).first()
        if not aggregate:
            aggregate = DailyAggregate(patient_id=str(payload.patient_id), stat_date=stat_date, average_score=0, average_accuracy=0, average_reaction_time=0)
            db.add(aggregate)
        aggregate.games_played = (aggregate.games_played or 0) + 1
        aggregate.sessions_completed = (aggregate.sessions_completed or 0) + int(payload.completed)
        aggregate.average_score = ((aggregate.average_score * (aggregate.games_played - 1)) + payload.score) / aggregate.games_played
        aggregate.average_accuracy = ((aggregate.average_accuracy * (aggregate.games_played - 1)) + payload.accuracy) / aggregate.games_played
        aggregate.average_reaction_time = ((aggregate.average_reaction_time * (aggregate.games_played - 1)) + payload.response_time) / aggregate.games_played
        aggregate.completion_rate = aggregate.sessions_completed / aggregate.games_played
        week_start = stat_date - timedelta(days=stat_date.weekday())
        weekly = db.query(WeeklyAggregate).filter_by(patient_id=str(payload.patient_id), week_start=week_start).first()
        if not weekly:
            weekly = WeeklyAggregate(patient_id=str(payload.patient_id), week_start=week_start)
            db.add(weekly)
        weekly.games_played = (weekly.games_played or 0) + 1
        weekly.average_score = ((weekly.average_score or 0) * (weekly.games_played - 1) + payload.score) / weekly.games_played
        weekly.average_accuracy = ((weekly.average_accuracy or 0) * (weekly.games_played - 1) + payload.accuracy) / weekly.games_played
        weekly.average_reaction_time = ((weekly.average_reaction_time or 0) * (weekly.games_played - 1) + payload.response_time) / weekly.games_played
    db.commit()
    response = {'status': 'synced', 'event_id': str(payload.event_id)}
    if pattern_decision:
        response.update({
            'cps': pattern_decision.cps,
            'components': pattern_decision.components,
            'next_difficulty': pattern_decision.next_difficulty,
            'next_activity': pattern_decision.next_activity,
            'model_used': pattern_decision.model_used,
            'confidence': pattern_decision.confidence,
            'caregiver_notification': pattern_decision.caregiver_notification,
            'explanation': pattern_decision.explanation,
        })
    return response

@app.post('/game-results', status_code=201)
def save_result(payload: ResultIn, user: Annotated[User, Depends(require_roles(Role.patient, Role.caregiver))], db: Annotated[Session, Depends(get_db)]):
    return store_result(payload, user, db)

@app.post('/sync')
def sync(payloads: list[ResultIn], user: Annotated[User, Depends(require_roles(Role.patient, Role.caregiver))], db: Annotated[Session, Depends(get_db)]):
    synced = 0
    duplicates = 0
    for payload in payloads:
        response = store_result(payload, user, db)
        synced += response['status'] == 'synced'
        duplicates += response['status'] == 'already_synced'
    return {'synced': synced, 'duplicates': duplicates}

@app.get('/patients/{patient_id}/games')
def game_history(patient_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: Annotated[User, Depends(get_current_user)] = None, db: Session = Depends(get_db)):
    can_access(db, user, str(patient_id))
    query = db.query(GameResult).join(GameSession, GameSession.id == GameResult.session_id).filter(GameSession.patient_id == str(patient_id))
    total = query.count()
    items = query.order_by(GameResult.recorded_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {'items': [{'event_id': item.event_id, 'score': item.score, 'accuracy': item.accuracy, 'game_type': db.get(GameSession, item.session_id).game_type} for item in items], 'page': page, 'page_size': page_size, 'total': total}

@app.get('/reminders')
def get_reminders(patient_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(patient_id))
    return db.query(Reminder).filter_by(patient_id=str(patient_id), enabled=True).order_by(Reminder.reminder_time).all()

@app.post('/reminders', status_code=201)
def add_reminder(payload: ReminderIn, user: Annotated[User, Depends(require_roles(Role.caregiver, Role.admin))], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(payload.patient_id))
    item = Reminder(patient_id=str(payload.patient_id), title=payload.title, description=payload.description, reminder_type=payload.reminder_type, reminder_time=payload.time, recurrence=payload.recurrence, enabled=payload.enabled)
    db.add(item)
    log(db, user, 'reminder.created')
    db.commit()
    db.refresh(item)
    return item

@app.put('/reminders/{reminder_id}')
def update_reminder(reminder_id: UUID, payload: ReminderIn, user: Annotated[User, Depends(require_roles(Role.caregiver, Role.admin))], db: Annotated[Session, Depends(get_db)]):
    item = db.get(Reminder, str(reminder_id))
    if not item: raise HTTPException(status_code=404, detail='Reminder not found')
    can_access(db, user, item.patient_id)
    item.title, item.description, item.reminder_type, item.reminder_time, item.recurrence, item.enabled = payload.title, payload.description, payload.reminder_type, payload.time, payload.recurrence, payload.enabled
    db.commit()
    db.refresh(item)
    return item

@app.delete('/reminders/{reminder_id}')
def delete_reminder(reminder_id: UUID, user: Annotated[User, Depends(require_roles(Role.caregiver, Role.admin))], db: Annotated[Session, Depends(get_db)]):
    item = db.get(Reminder, str(reminder_id))
    if not item:
        raise HTTPException(status_code=404, detail='Reminder not found')
    can_access(db, user, item.patient_id)
    item.enabled = False
    db.commit()
    return {'status': 'disabled'}

@app.patch('/reminders/{reminder_id}/complete')
def complete_reminder(reminder_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    item = db.get(Reminder, str(reminder_id))
    if not item: raise HTTPException(status_code=404, detail='Reminder not found')
    can_access(db, user, item.patient_id)
    item.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {'status': 'completed', 'reminder_id': item.id}

@app.get('/patients/{patient_id}/stats')
def stats(patient_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(patient_id))
    rows = db.query(DailyAggregate).filter_by(patient_id=str(patient_id)).order_by(DailyAggregate.stat_date.desc()).limit(7).all()
    return {'games_completed': sum(row.sessions_completed for row in rows), 'average_accuracy': round(sum(row.average_accuracy for row in rows) / len(rows), 2) if rows else 0, 'performance': {'memory': 82, 'attention': 68, 'pattern': 76}}

@app.get('/analytics/patients/{patient_id}/daily')
def daily_analytics(patient_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100), user: Annotated[User, Depends(get_current_user)] = None, db: Session = Depends(get_db)):
    can_access(db, user, str(patient_id))
    query = db.query(DailyAggregate).filter_by(patient_id=str(patient_id)).order_by(DailyAggregate.stat_date.desc())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {'items': [{'date': row.stat_date, 'games_played': row.games_played, 'sessions_completed': row.sessions_completed, 'average_score': row.average_score, 'average_accuracy': row.average_accuracy, 'average_reaction_time': row.average_reaction_time, 'completion_rate': row.completion_rate} for row in rows], 'page': page, 'page_size': page_size}

@app.get('/analytics/patients/{patient_id}/weekly')
def weekly_analytics(patient_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(patient_id))
    since = date.today() - timedelta(days=6)
    rows = db.query(DailyAggregate).filter(DailyAggregate.patient_id == str(patient_id), DailyAggregate.stat_date >= since).all()
    count = sum(row.games_played for row in rows)
    return {'patient_id': str(patient_id), 'period_days': 7, 'games_played': count, 'average_score': sum(row.average_score * row.games_played for row in rows) / count if count else 0, 'average_accuracy': sum(row.average_accuracy * row.games_played for row in rows) / count if count else 0, 'average_reaction_time': sum(row.average_reaction_time * row.games_played for row in rows) / count if count else 0}

@app.get('/recommendations/{patient_id}')
def recommendation(patient_id: UUID, game_type: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(patient_id))
    if game_type == 'PATTERN_RECOGNITION':
        latest = db.query(GameResult).join(GameSession, GameSession.id == GameResult.session_id).filter(
            GameSession.patient_id == str(patient_id),
            GameSession.game_type == game_type,
            GameResult.completed.is_(True),
        ).order_by(GameResult.recorded_at.desc()).first()
        if latest and latest.cps is not None:
            return {
                'game_type': game_type,
                'cps': latest.cps,
                'components': {
                    'accuracy': latest.accuracy_component,
                    'reaction': latest.reaction_component,
                    'completion': latest.completion_component,
                    'consistency': latest.consistency_component,
                },
                'score': latest.score,
                'accuracy_percent': round(latest.accuracy * 100, 1),
                'response_time': latest.response_time,
                'attempts': latest.attempts,
                'previous_difficulty': db.get(GameSession, latest.session_id).difficulty_level,
                'next_difficulty': latest.recommended_difficulty,
                'next_activity': latest.recommended_activity,
                'model_used': latest.recommendation_model,
                'caregiver_notification': latest.caregiver_notification,
                'explanation': latest.recommendation_explanation,
            }
    recent = db.query(GameResult.accuracy).join(GameSession, GameSession.id == GameResult.session_id).filter(GameSession.patient_id == str(patient_id), GameSession.game_type == game_type).order_by(GameResult.recorded_at.desc()).limit(3).all()
    values = [row[0] for row in recent]
    decision = recommend_difficulty(values[0] if values else .7, 2, values[1:])
    return {'game_type': game_type, 'next_difficulty': decision.next_difficulty, 'explanation': decision.explanation}

@app.get('/alerts/{patient_id}')
def alerts(patient_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    can_access(db, user, str(patient_id))
    now = datetime.now(timezone.utc)
    missed = db.query(Reminder).filter(Reminder.patient_id == str(patient_id), Reminder.enabled.is_(True), Reminder.completed_at.is_(None)).all()
    for reminder in missed:
        if reminder.reminder_time < now.strftime('%H:%M') and reminder.start_date <= now.date() and (not reminder.end_date or reminder.end_date >= now.date()):
            exists = db.query(Alert).filter(Alert.patient_id == str(patient_id), Alert.message == 'Several reminders may have been missed. Please review the daily schedule.', Alert.created_at >= datetime.combine(now.date(), datetime.min.time())).first()
            if not exists:
                db.add(Alert(patient_id=str(patient_id), message='Several reminders may have been missed. Please review the daily schedule.', status='new'))
                db.commit()
            break
    recent = db.query(GameResult).join(GameSession, GameSession.id == GameResult.session_id).filter(GameSession.patient_id == str(patient_id), GameResult.recorded_at >= now - timedelta(days=3)).count()
    if recent == 0:
        exists = db.query(Alert).filter(Alert.patient_id == str(patient_id), Alert.message == 'Recent activity is lower than usual. Please review the daily routine.', Alert.created_at >= now - timedelta(days=1)).first()
        if not exists:
            db.add(Alert(patient_id=str(patient_id), message='Recent activity is lower than usual. Please review the daily routine.', status='new'))
            db.commit()
    return db.query(Alert).filter_by(patient_id=str(patient_id)).order_by(Alert.created_at.desc()).all()

@app.patch('/alerts/{alert_id}/acknowledge')
def acknowledge_alert(alert_id: UUID, user: Annotated[User, Depends(require_roles(Role.caregiver, Role.admin, Role.healthcare_worker))], db: Annotated[Session, Depends(get_db)]):
    alert = db.get(Alert, str(alert_id))
    if not alert: raise HTTPException(status_code=404, detail='Alert not found')
    can_access(db, user, alert.patient_id)
    alert.status = 'acknowledged'
    db.commit()
    return {'status': alert.status, 'alert_id': alert.id}
