from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4

client = TestClient(app)


def test_health():
    assert client.get('/health').json() == {'status': 'ok'}


def test_duplicate_sync_is_idempotent():
    payload = {
        'event_id': str(uuid4()),
        'patient_id': '11111111-1111-1111-1111-111111111111',
        'game_type': 'MEMORY_MATCH', 'difficulty_level': 2, 'score': 8,
        'accuracy': 0.8, 'response_time': 2.2, 'attempts': 1, 'completed': True,
    }
    first = client.post('/game-results', json=payload)
    second = client.post('/game-results', json=payload)
    assert first.json()['status'] == 'synced'
    assert second.json()['status'] == 'already_synced'


def test_caregiver_cannot_access_unassigned_patient():
    response = client.get('/patients/99999999-9999-9999-9999-999999999999', headers={'X-Demo-User': 'caregiver-demo'})
    assert response.status_code == 403


def test_login_returns_jwt_and_me_accepts_it():
    response = client.post('/auth/login', json={'email': 'caregiver@mindner.local', 'password': 'demo-password'})
    assert response.status_code == 200
    assert response.json()['token_type'] == 'cookie'
    assert 'mindner_access_token' in response.cookies
    me = client.get('/auth/me')
    assert me.status_code == 200
    assert me.json()['role'] == 'CAREGIVER'


def test_adaptive_recommendation_is_explainable():
    response = client.get('/recommendations/11111111-1111-1111-1111-111111111111?game_type=MEMORY_MATCH')
    assert response.status_code == 200
    assert response.json()['next_difficulty'] in (1, 2, 3)
    assert response.json()['explanation']


def test_pattern_result_persists_cps_and_returns_difficulty_recommendation():
    patient_id = '11111111-1111-1111-1111-111111111111'
    payload = {
        'event_id': str(uuid4()), 'patient_id': patient_id,
        'game_type': 'PATTERN_RECOGNITION', 'difficulty_level': 2,
        'score': 80, 'accuracy': 0.8, 'response_time': 6,
        'attempts': 4, 'mistakes': 1, 'completed': True,
    }
    saved = client.post('/game-results', json=payload)
    assert saved.status_code == 201
    result = saved.json()
    assert result['status'] == 'synced'
    assert 0 <= result['cps'] <= 100
    assert result['components']['accuracy'] == 80
    assert result['next_difficulty'] in (1, 2, 3)
    recommendation = client.get(f'/recommendations/{patient_id}?game_type=PATTERN_RECOGNITION')
    assert recommendation.status_code == 200
    assert recommendation.json()['cps'] == result['cps']
    assert recommendation.json()['next_difficulty'] == result['next_difficulty']


def test_low_pattern_cps_requests_caregiver_review():
    payload = {
        'event_id': str(uuid4()), 'patient_id': '11111111-1111-1111-1111-111111111111',
        'game_type': 'PATTERN_RECOGNITION', 'difficulty_level': 3,
        'score': 1, 'accuracy': 0.01, 'response_time': 1000,
        'attempts': 10, 'mistakes': 99, 'completed': False,
    }
    response = client.post('/game-results', json=payload)
    assert response.status_code == 201
    assert response.json()['cps'] < 40
    assert response.json()['caregiver_notification'] is True
    assert response.json()['next_activity'] == 'GUIDED_EASY_ACTIVITY'
