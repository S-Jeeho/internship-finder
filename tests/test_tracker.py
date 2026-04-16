"""Tests for src/storage/tracker.py"""

from pathlib import Path

import pytest

from src.companies.models import Company
from src.storage.tracker import Tracker


def test_save_companies_inserts_rows(tmp_db: Path, sample_company_list: list) -> None:
    tracker = Tracker(tmp_db)
    inserted = tracker.save_companies(sample_company_list)
    assert inserted == 2
    assert tracker.count_companies() == 2


def test_save_companies_ignores_duplicates(tmp_db: Path, sample_company: Company) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies([sample_company])
    inserted_again = tracker.save_companies([sample_company])
    assert inserted_again == 0
    assert tracker.count_companies() == 1


def test_get_uncontacted_returns_all_when_none_emailed(
    tmp_db: Path, sample_company_list: list
) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies(sample_company_list)
    uncontacted = tracker.get_uncontacted_companies()
    assert len(uncontacted) == 2


def test_mark_emailed_excludes_from_uncontacted(tmp_db: Path, sample_company: Company) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies([sample_company])
    tracker.mark_emailed(sample_company.company_number, "sent", gmail_message_id="msg_abc")
    uncontacted = tracker.get_uncontacted_companies()
    assert len(uncontacted) == 0


def test_failed_company_is_still_uncontacted(tmp_db: Path, sample_company: Company) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies([sample_company])
    tracker.mark_emailed(
        sample_company.company_number, "failed", error_message="SMTP error"
    )
    uncontacted = tracker.get_uncontacted_companies()
    # Failed attempt should NOT block retry
    assert len(uncontacted) == 1


def test_has_been_emailed_true_after_sent(tmp_db: Path, sample_company: Company) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies([sample_company])
    tracker.mark_emailed(sample_company.company_number, "sent")
    assert tracker.has_been_emailed(sample_company.company_number) is True


def test_has_been_emailed_false_for_failed(tmp_db: Path, sample_company: Company) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies([sample_company])
    tracker.mark_emailed(sample_company.company_number, "failed")
    assert tracker.has_been_emailed(sample_company.company_number) is False


def test_has_been_emailed_false_for_unknown(tmp_db: Path) -> None:
    tracker = Tracker(tmp_db)
    assert tracker.has_been_emailed("NONEXISTENT") is False


def test_get_email_log_returns_entries(tmp_db: Path, sample_company: Company) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies([sample_company])
    tracker.mark_emailed(sample_company.company_number, "sent", gmail_message_id="msg_xyz")
    log = tracker.get_email_log()
    assert len(log) == 1
    assert log[0]["status"] == "sent"
    assert log[0]["gmail_message_id"] == "msg_xyz"


def test_count_sent(tmp_db: Path, sample_company_list: list) -> None:
    tracker = Tracker(tmp_db)
    tracker.save_companies(sample_company_list)
    tracker.mark_emailed(sample_company_list[0].company_number, "sent")
    tracker.mark_emailed(sample_company_list[1].company_number, "failed")
    assert tracker.count_sent() == 1
