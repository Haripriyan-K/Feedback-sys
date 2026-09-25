import os
import tempfile
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.gettempdir(), 'test_feedback.db')

from app import app as flask_app, db, Feedback  # noqa: E402


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as client:
        with flask_app.app_context():
            db.drop_all()
            db.create_all()
        yield client
        with flask_app.app_context():
            db.drop_all()


def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'healthy'


def test_feedback_form_get(client):
    resp = client.get('/feedback')
    assert resp.status_code == 200
    assert b'Share your feedback' in resp.data


def test_feedback_submit(client):
    resp = client.post('/feedback', data={
        'name': 'Test User',
        'register_no': 'RA123',
        'department': 'Computer Science',
        'category': 'Academics',
        'rating': '5',
        'comments': 'Great experience',
    }, follow_redirects=True)
    assert resp.status_code == 200
    with flask_app.app_context():
        assert Feedback.query.count() == 1


def test_feedback_submit_invalid_rating(client):
    resp = client.post('/feedback', data={
        'name': 'Test User',
        'register_no': 'RA123',
        'department': 'Computer Science',
        'category': 'Academics',
        'rating': '9',
        'comments': '',
    })
    assert resp.status_code == 200
    with flask_app.app_context():
        assert Feedback.query.count() == 0


def test_admin_login_required(client):
    resp = client.get('/admin/dashboard', follow_redirects=True)
    assert b'Admin Login' in resp.data


def test_admin_login_success_and_dashboard(client):
    resp = client.post('/admin/login', data={
        'username': 'admin', 'password': 'admin123'
    }, follow_redirects=True)
    assert b'Dashboard' in resp.data or resp.status_code == 200

    resp2 = client.get('/admin/dashboard')
    assert resp2.status_code == 200
    assert b'Total Feedback' in resp2.data


def test_admin_login_failure(client):
    resp = client.post('/admin/login', data={
        'username': 'wrong', 'password': 'wrong'
    })
    assert b'Invalid username or password' in resp.data


def test_toggle_status(client):
    client.post('/feedback', data={
        'name': 'Test User', 'register_no': 'RA123',
        'department': 'Computer Science', 'category': 'Academics',
        'rating': '4', 'comments': 'ok',
    })
    client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
    with flask_app.app_context():
        fb = Feedback.query.first()
        fb_id = fb.id
        assert fb.status == 'pending'
    client.post(f'/admin/feedback/{fb_id}/toggle-status', follow_redirects=True)
    with flask_app.app_context():
        assert Feedback.query.get(fb_id).status == 'resolved'
