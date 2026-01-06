"""Testing module for :py:mod:`issues.base` module."""

import pytest

from issues.base import BaseIssueProvider


class DummyBaseIssueProvider(BaseIssueProvider):

    def _get_client(self, issue_tracker_api_token):
        super()._get_client(issue_tracker_api_token)
        return f"{issue_tracker_api_token}"

    def _get_repository(self):
        super()._get_repository()
        return "repo"

    def _close_issue_with_labels_impl(self, issue_number, labels_to_set, comment):
        super()._close_issue_with_labels_impl(issue_number, labels_to_set, comment)
        return f"{issue_number} {labels_to_set} {comment}"

    def _create_issue_impl(self, title, body, labels):
        super()._create_issue_impl(title, body, labels)
        return f"title: {title}, body: {body} labels:{labels}"

    def _fetch_issues_impl(self, state, since):
        super()._fetch_issues_impl(state, since)
        return f"state: {state} since: {since}"

    def _get_issue_by_number_impl(self, issue_number):
        super()._get_issue_by_number_impl(issue_number)
        return issue_number

    def _issue_url_impl(self, issue_number):
        super()._issue_url_impl(issue_number)
        return issue_number

    def _set_labels_to_issue_impl(self, issue_number, labels_to_set):
        super()._set_labels_to_issue_impl(issue_number, labels_to_set)
        return f"issue_number: {issue_number} labels_to_set: {labels_to_set}"


class TestBaseIssueProvider:
    """Testing class for :class:`issues.base.BaseIssueProvider` interface."""

    def test_issues_base_baseissueprovider_is_abstract(self):
        with pytest.raises(TypeError) as exc_info:
            BaseIssueProvider()

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_issues_base_baseissueprovider_get_client(self):
        c = DummyBaseIssueProvider(None)
        assert c._get_client("ABC") == "ABC"

    def test_issues_base_baseissueprovider_get_repository(self):
        c = DummyBaseIssueProvider(None)
        assert c._get_repository() == "repo"

    def test_issues_base_baseissueprovider_close_issue_with_labels_impl(self):
        c = DummyBaseIssueProvider(None)
        assert (
            c._close_issue_with_labels_impl("issue_number", "labels_to_set", "comment")
            == "issue_number labels_to_set comment"
        )

    def test_issues_base_baseissueprovider_create_issue_impl(self):
        c = DummyBaseIssueProvider(None)
        assert (
            c._create_issue_impl("title", "body", "labels")
            == "title: title, body: body labels:labels"
        )

    def test_issues_base_baseissueprovider_fetch_issues_impl(self):
        c = DummyBaseIssueProvider(None)
        assert c._fetch_issues_impl("state", "since") == "state: state since: since"

    def test_issues_base_baseissueprovider_get_issue_by_number_impl(self):
        c = DummyBaseIssueProvider(None)
        assert c._get_issue_by_number_impl("issue_number") == "issue_number"

    def test_issues_base_baseissueprovider_issue_url_impl(self):
        c = DummyBaseIssueProvider(None)
        assert c._issue_url_impl("issue_number") == "issue_number"

    def test_issues_base_baseissueprovider_set_labels_to_issue_impl(self):
        c = DummyBaseIssueProvider(None)
        assert (
            c._set_labels_to_issue_impl("issue_number", "labels_to_set")
            == "issue_number: issue_number labels_to_set: labels_to_set"
        )


class TestIssuesBaseBaseIssueProvider:
    """Testing class for :py:mod:`issues.base.BaseIssueProvider` class."""

    @pytest.mark.parametrize(
        "attr",
        ["name", "user", "client", "repo"],
    )
    def test_issues_base_baseissueprovider_inits_attribute_as_none(self, attr):
        assert getattr(BaseIssueProvider, attr) is None
