# Memo App

A CLI memo application built with **Clean Architecture** in Python. No external dependencies — only the standard library + pytest for testing.

## Architecture

```
Entity (dataclass)  →  UseCase (business logic)  →  Repository (SQLite)
                                                  →  Controller (CLI)
                                                  →  View (output)
```

| Layer | File | Responsibility |
|-------|------|----------------|
| Entity | `entity.py` | Immutable data models (Memo, Tag, User) |
| UseCase | `usecase.py` | Business logic, validation, authorization |
| Repository | `repository.py` | Abstract interface + SQLite implementation |
| Controller | `controller.py` | CLI command routing, session verification |
| View | `view.py` | Output formatting (no DB/business knowledge) |
| Auth | `auth.py` | Salted SHA-256 password hashing |
| Session | `session.py` | Token-based session management |

## Features

**Authentication:**
- `register <username>` — Create account (username 3+ chars, password 8+ chars)
- `login <username>` — Login with token-based session (7-day expiry)
- `logout` / `whoami` — Session management

**Memo Operations (login required):**
- `add "content"` — Create memo
- `list` — List your memos (with tags)
- `edit <id> "content"` — Edit memo (owner only)
- `delete <id>` — Delete memo (owner only)
- `tag <id> "tag"` / `untag <id> "tag"` — Manage tags
- `search "tag"` — Search by tag
- `tags` — List all tags

## Security

- Salted SHA-256 password hashing (same password → different hash each time)
- Authorization checks on all memo operations (owner-only access)
- Ambiguous error messages to prevent user enumeration attacks
- Hidden password input via `getpass`
- Session tokens with DB-side validation and expiry

## Database

SQLite with schema versioning (v0 → v1 → v2):
- Foreign key constraints with CASCADE delete
- Many-to-many relationship via `memo_tags` junction table
- Indexed queries for performance

## Testing

```bash
pip install -r requirements.txt
pytest -v
```

**78 tests** across 4 files:

| File | Tests | Coverage |
|------|-------|----------|
| `test_entity.py` | Immutability, data model creation | Entity layer |
| `test_repository.py` | CRUD, tag relations, user filtering | Repository layer |
| `test_usecase.py` | Business logic, auth flow, authorization | UseCase layer |
| `test_auth.py` | Hash generation, verification, salt uniqueness | Auth module |

Tests use **Fake Repository** pattern — no database required for testing.

## Quick Start

```bash
python app.py register myuser
python app.py login myuser
python app.py add "Buy milk"
python app.py list
```

## Tech Stack

- **Python 3.12** — Standard library only (no pip dependencies for production)
- **SQLite** — Embedded database
- **pytest** — Testing framework
- **Clean Architecture** — Layered design with dependency inversion
