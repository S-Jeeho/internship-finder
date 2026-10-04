# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- `src/ppt_creator/` — new package scaffold for PowerPoint generation
- Step 1: Project skeleton — directory structure, CHANGELOG, .gitignore, .env.example, requirements.txt
- Step 1: `config/settings.py` — loads and validates all environment variables
- Step 1: `config/sic_codes.py` — UK SIC 2007 biology sector codes
- Step 1: `src/companies/models.py` — `Company` dataclass (canonical data schema)
- Step 2: `src/storage/database.py` — SQLite connection manager + schema creation
- Step 2: `src/storage/tracker.py` — company/email state tracking CRUD
- Step 2: `tests/test_database.py`, `tests/test_tracker.py`
- Step 3: `src/companies/companies_house.py` — Companies House REST API client (paginated, SIC-filtered)
- Step 3: `tests/test_companies_house.py`
- Step 4: `src/companies/geocoder.py` — Google Maps geocoding + Haversine distance filter
- Step 4: `tests/test_geocoder.py`
- Step 5: `src/cv/tailorer.py` — Claude API CV tailoring with length validation
- Step 5: `tests/test_tailorer.py`
- Step 6: `src/cv/pdf_builder.py` — Markdown → HTML → PDF via WeasyPrint
- Step 6: `tests/test_pdf_builder.py`
- Step 7: `src/email/gmail_auth.py` — Gmail OAuth2 credential lifecycle
- Step 7: `tests/test_gmail_auth.py`
- Step 8: `src/email/templates.py` — email subject/body templates
- Step 8: `src/email/gmail_sender.py` — composes MIME message, attaches PDF, sends via Gmail API
- Step 8: `tests/test_gmail_sender.py`
- Step 9: `src/pipeline/runner.py` — end-to-end orchestrator with dry-run support
- Step 9: `tests/test_runner.py`
- Step 10: `scripts/run_pipeline.py`, `scripts/fetch_companies_only.py`, `scripts/revoke_gmail_token.py`
