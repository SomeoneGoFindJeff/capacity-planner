# tests/conftest.py
import pytest
from app import app as flask_app, db

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    with flask_app.app_context():
        db.create_all()
    yield flask_app
    # teardown
    with flask_app.app_context():
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
