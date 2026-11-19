"""Tests for streaming.services.get_connection_details.main().

Run from your Django backend root:
    pytest -q test_get_connection_details.py

Requires pytest and Django test settings (usually configured via pytest-django).
These tests mock Redis scanning and credential lookup; no external services are used.
"""
from unittest.mock import patch

import pytest

from streaming.services import get_connection_details as service


DETAILS_ORDERS = {
    "dbname": "nike",
    "user": "test_user",
    "password": "test_password",
    "host": "localhost",
    "port": 5432,
    "sslmode": "require",
    "datasource_id": "source-1",
    "table_id": "orders-1",
    "table_name": "orders",
}


def session(table_id="orders-1"):
    return {"datasource_id": "source-1", "table_id": table_id, "user_id": "7"}


def test_no_active_sessions_returns_none():
    with patch.object(service, "scan_userSession", return_value={}), \
         patch.object(service, "get_connection_details") as lookup:
        assert service.main() is None
        lookup.assert_not_called()


def test_one_active_session_looks_up_correct_table():
    sessions = {"user-session:7": session()}
    with patch.object(service, "scan_userSession", return_value=sessions), \
         patch.object(service, "get_connection_details", return_value=DETAILS_ORDERS) as lookup:
        assert service.main() == DETAILS_ORDERS
        lookup.assert_called_once_with("source-1", "orders-1")


def test_two_users_same_table_only_one_lookup_with_current_implementation():
    sessions = {
        "user-session:7": session(),
        "user-session:8": {**session(), "user_id": "8"},
    }
    with patch.object(service, "scan_userSession", return_value=sessions), \
         patch.object(service, "get_connection_details", return_value=DETAILS_ORDERS) as lookup:
        assert service.main() == DETAILS_ORDERS
        lookup.assert_called_once_with("source-1", "orders-1")
    # WARNING: This passes because main() returns after the FIRST session.
    # It does NOT prove that the implementation properly deduplicates tables.


@pytest.mark.xfail(strict=True, reason="main() currently returns after the first session")
def test_two_different_tables_should_both_be_selected():
    sessions = {
        "user-session:7": session("orders-1"),
        "user-session:8": {**session("products-1"), "user_id": "8"},
    }
    with patch.object(service, "scan_userSession", return_value=sessions), \
         patch.object(service, "get_connection_details", return_value=DETAILS_ORDERS) as lookup:
        service.main()
        assert lookup.call_count == 2
