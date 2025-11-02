import os
import sys
import pytest

# Ensure project root is on sys.path for imports when running via pytest
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    app.config.update({
        'TESTING': True,
    })
    return app


@pytest.fixture
def client(app):
    return app.test_client()