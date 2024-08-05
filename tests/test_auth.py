import pytest
import sys
from unittest.mock import patch, MagicMock

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import utils


def mock_storage_adapter(tokens=None):
    mock = MagicMock()
    mock.get_by_resource_server.return_value = tokens
    return mock


@pytest.fixture
def clear_cache():
    """Fixture to clear the cache before each test."""
    utils._cache.clear()


@pytest.fixture
def mock_storage():
    with patch("utils.storage_adapter", new=mock_storage_adapter()) as mock:
        yield mock


def test_token_in_cache(clear_cache):
    utils._cache["any_scope_id"] = "SAMPLE_TOKEN"
    assert utils.get_access_token("any_scope_id") == "SAMPLE_TOKEN"


def test_no_scope_id(clear_cache, mock_storage):
    mock_storage().get_by_resource_server.return_value = None
    assert utils.get_access_token("") == "INVALID_TOKEN"


def test_no_tokens(clear_cache, mock_storage):
    mock_storage().get_by_resource_server.return_value = None
    assert utils.get_access_token("scope_id") == "INVALID_TOKEN"


def test_scope_id_not_in_tokens(clear_cache, mock_storage):
    mock_storage().get_by_resource_server.return_value = {
        "different_scope_id": {"access_token": "VALID_TOKEN"}
    }
    with pytest.raises(utils.UnauthorizedError):
        utils.get_access_token("scope_id")


def test_auth_data_and_valid_token(clear_cache, mock_storage):
    mock_storage().get_by_resource_server.return_value = {
        "scope_id": {"access_token": "VALID_TOKEN"}
    }
    assert utils.get_access_token("scope_id") == "VALID_TOKEN"


def test_no_auth_data_for_scope_id(clear_cache, mock_storage):
    mock_storage().get_by_resource_server.return_value = {"scope_id": {}}
    with pytest.raises(utils.UnauthorizedError):
        utils.get_access_token("scope_id")


def test_subsequent_calls_use_cached_token(clear_cache, mock_storage):
    ## In this case the cached token persists
    mock_storage().get_by_resource_server.return_value = {
        "scope_id": {"access_token": "VALID_TOKEN_1"}
    }
    assert utils.get_access_token("scope_id") == "VALID_TOKEN_1"
    mock_storage().get_by_resource_server.return_value = {
        "scope_id": {"access_token": "VALID_TOKEN_2"}
    }
    assert utils.get_access_token("scope_id") == "VALID_TOKEN_1"
