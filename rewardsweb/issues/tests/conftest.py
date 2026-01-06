"""Pytest configuration for issues package tests."""

import pytest
from django.test import RequestFactory

@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def github_webhook_payload():
    return {
        "action": "opened",
        "issue": {
            "number": 123,
            "title": "Test Issue",
            "body": "Test issue body",
            "html_url": "https://github.com/test/repo/issues/123",
            "user": {"login": "testuser"},
            "created_at": "2023-01-01T00:00:00Z",
            "state": "open",
        },
        "repository": {"full_name": "test/repo"},
    }


@pytest.fixture
def gitlab_webhook_payload():
    return {
        "object_kind": "issue",
        "object_attributes": {
            "action": "open",
            "title": "Test Issue",
            "description": "Test description",
            "iid": 123,
            "url": "https://gitlab.com/test/project/issues/123",
            "author": {"username": "testuser"},
            "created_at": "2023-01-01T00:00:00Z",
            "state": "opened",
        },
        "project": {"id": 456, "name": "test-project"},
    }


@pytest.fixture
def bitbucket_webhook_payload():
    return {
        "changes": {"created": True},
        "issue": {
            "id": 123,
            "title": "Test Issue",
            "content": {"raw": "Test content"},
            "state": "new",
            "reporter": {"display_name": "testuser"},
            "links": {"html": {"href": "https://bitbucket.org/test/repo/issues/123"}},
            "created_on": "2023-01-01T00:00:00Z",
        },
        "repository": {"full_name": "test/repo"},
    }
