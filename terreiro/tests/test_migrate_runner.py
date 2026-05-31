"""Tests that the migration runner (scripts/migrate.py) is wired to yoyo.

There is no live DB here (the suite uses a mocked asyncpg pool). These tests
prove the CLI surface: DSN/dir resolution and the exact yoyo command the runner
shells out to in both `apply` and `--mark-only` modes. `subprocess.run` is
patched so nothing actually executes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# scripts/migrate.py lives at the repo root, outside the `terreiro` package, so
# load it by file path: tests/ -> terreiro/ -> repo root -> scripts/migrate.py.
_MIGRATE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "migrate.py"
)


def _load_migrate():
    spec = importlib.util.spec_from_file_location("migrate_runner", _MIGRATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def migrate():
    return _load_migrate()


class TestDsnResolution:
    def test_argv_override_wins(self, migrate, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["migrate.py", "postgresql://x@h/d"])
        monkeypatch.setenv("DATABASE_URL", "postgresql://env@h/d")
        assert migrate.resolve_dsn() == "postgresql://x@h/d"

    def test_flags_are_not_treated_as_dsn(self, migrate, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["migrate.py", "--mark-only"])
        monkeypatch.setenv("DATABASE_URL", "postgresql://env@h/d")
        assert migrate.resolve_dsn() == "postgresql://env@h/d"

    def test_falls_back_to_database_url(self, migrate, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["migrate.py"])
        monkeypatch.setenv("DATABASE_URL", "postgresql://env@h/d")
        assert migrate.resolve_dsn() == "postgresql://env@h/d"

    def test_local_default_last(self, migrate, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["migrate.py"])
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert migrate.resolve_dsn() == "postgresql://maracatu:changeme@db:5432/maracatu"


class TestMigrationsDir:
    def test_repo_fallback_exists(self, migrate):
        # /app/migrations does not exist locally, so it falls back to the repo
        # terreiro/migrations directory, which must exist and hold the SQL files.
        d = migrate.resolve_migrations_dir()
        assert d.exists()
        assert (d / "0001.create-tables.sql").exists()


class TestYoyoInvocation:
    def _run(self, migrate, monkeypatch, argv):
        monkeypatch.setattr(sys, "argv", argv)
        monkeypatch.setenv("DATABASE_URL", "postgresql://env@h/d")
        captured = {}

        def fake_run(cmd, check):  # noqa: ANN001
            captured["cmd"] = cmd
            captured["check"] = check
            return MagicMock(returncode=0)

        monkeypatch.setattr(migrate.subprocess, "run", fake_run)
        migrate.main()
        return captured

    def test_apply_mode_default(self, migrate, monkeypatch):
        captured = self._run(migrate, monkeypatch, ["migrate.py"])
        cmd = captured["cmd"]
        assert cmd[0] == "yoyo"
        assert cmd[1] == "apply"
        assert "--batch" in cmd
        assert "--database" in cmd
        assert cmd[cmd.index("--database") + 1] == "postgresql://env@h/d"
        # the migrations dir is the final positional argument
        assert cmd[-1] == str(migrate.resolve_migrations_dir())
        assert captured["check"] is True

    def test_mark_only_mode(self, migrate, monkeypatch):
        # mark is only legal while just the legacy migrations are on disk; the
        # guard checks the dir, so simulate the legacy-only state.
        monkeypatch.setattr(migrate, "has_post_legacy_migrations", lambda d: False)
        captured = self._run(migrate, monkeypatch, ["migrate.py", "--mark-only"])
        cmd = captured["cmd"]
        assert cmd[1] == "mark"
        assert "--batch" in cmd
        assert cmd[cmd.index("--database") + 1] == "postgresql://env@h/d"

    def test_mark_refused_when_retrofit_present(self, migrate, monkeypatch):
        # With 0018+ migrations on disk, marking would silently skip the UUID
        # conversion. The guard must refuse with a non-zero exit and never shell out.
        monkeypatch.setattr(migrate, "has_post_legacy_migrations", lambda d: True)
        monkeypatch.setattr(sys, "argv", ["migrate.py", "--mark-only"])
        monkeypatch.setenv("DATABASE_URL", "postgresql://env@h/d")

        def fail_if_called(cmd, check):  # noqa: ANN001
            raise AssertionError("subprocess.run must not run when mark is refused")

        monkeypatch.setattr(migrate.subprocess, "run", fail_if_called)
        with pytest.raises(SystemExit) as exc:
            migrate.main()
        assert exc.value.code == 1

    def test_force_mark_all_bypasses_guard(self, migrate, monkeypatch):
        # The explicit override lets mark proceed even with retrofit files present.
        monkeypatch.setattr(migrate, "has_post_legacy_migrations", lambda d: True)
        captured = self._run(
            migrate, monkeypatch, ["migrate.py", "--mark-only", "--force-mark-all"]
        )
        assert captured["cmd"][1] == "mark"

    def test_has_post_legacy_migrations_detects_retrofit(self, migrate):
        # The real terreiro/migrations dir holds 0018+ retrofit files.
        assert migrate.has_post_legacy_migrations(migrate.resolve_migrations_dir())

    def test_failure_propagates_exit_code(self, migrate, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["migrate.py"])
        monkeypatch.setenv("DATABASE_URL", "postgresql://env@h/d")

        def boom(cmd, check):  # noqa: ANN001
            raise migrate.subprocess.CalledProcessError(returncode=3, cmd=cmd)

        monkeypatch.setattr(migrate.subprocess, "run", boom)
        with pytest.raises(SystemExit) as exc:
            migrate.main()
        assert exc.value.code == 3
