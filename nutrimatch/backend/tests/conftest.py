import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base, get_db, make_engine
from app.main import create_app
from app.seed.seed import run_seed

DEMO_EMAIL = "demo@nutrimatch.local"


@pytest.fixture
def engine():
    # One shared in-memory connection so every session in a test sees the same database.
    test_engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory) -> Session:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db) -> Session:
    run_seed(db, DEMO_EMAIL)
    return db


@pytest.fixture
def client(seeded_db, session_factory):
    application = create_app()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as test_client:
        yield test_client
