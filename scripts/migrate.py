"""Apply SQL migrations via the yoyo-migrations runner.

This is the entrypoint mounted into the `api` container at /scripts/migrate.py
and invoked by `make db-migrate`. It is a thin wrapper around the `yoyo` CLI
(declared in terreiro/pyproject.toml, installed in the venv on PATH inside the
image). yoyo tracks applied migrations in its own state table `_yoyo_migration`,
so it applies only the unapplied files, each in its own transaction, with a real
rollback companion (`<name>.rollback.sql`).

Two modes:
  - default: `yoyo apply --batch` (applies unapplied migrations).
  - `--mark-only`: `yoyo mark --batch` (records every migration as applied
    WITHOUT running its SQL). Used exactly once when adopting yoyo against an
    existing prod schema whose 18 legacy idempotent migrations are already
    reflected in the live tables. Marking them applied prevents yoyo from
    re-running raw SQL it did not author, while keeping the state table aligned
    with reality. Run via `make db-migrate-mark`.
"""

import os
import subprocess
import sys
from pathlib import Path


def resolve_dsn() -> str:
    """Resolve the DSN from (1) an explicit argv override, (2) DATABASE_URL from
    the environment (how every container, prod included, gets its real
    credentials), and only then (3) the local-dev default. The default must
    never be relied on in prod: the real password lives in DATABASE_URL."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        return args[0]
    return os.environ.get(
        "DATABASE_URL", "postgresql://maracatu:changeme@db:5432/maracatu"
    )


LEGACY_MAX_PREFIX = 17
"""Highest numeric prefix among the legacy idempotent migrations (0001-0017).

`yoyo mark` records every migration on disk as applied WITHOUT running its SQL.
Marking is only ever correct for the legacy set, against a prod schema those
migrations already produced. If the retrofit migrations (0018+) are present when
mark runs, the entire conversion would be silently recorded as applied while no
DDL ran, and UUID-expecting code would then go live against int columns. So mark
refuses when any 0018+ file is on disk, unless explicitly forced."""


def has_post_legacy_migrations(migrations_dir: Path) -> bool:
    """True if any forward migration with a numeric prefix > LEGACY_MAX_PREFIX
    exists in the directory (rollback companions are ignored)."""
    for f in migrations_dir.glob("*.sql"):
        if ".rollback." in f.name:
            continue
        prefix = f.name.split(".", 1)[0]
        if prefix.isdigit() and int(prefix) > LEGACY_MAX_PREFIX:
            return True
    return False


def resolve_migrations_dir() -> Path:
    """Resolve the migrations directory the same way the legacy runner did:
    the in-container path first, then the repo-relative fallback for local
    invocations outside Docker."""
    migrations_dir = Path("/app/migrations")
    if not migrations_dir.exists():
        migrations_dir = (
            Path(__file__).resolve().parent.parent / "terreiro" / "migrations"
        )
    return migrations_dir


def main() -> None:
    dsn = resolve_dsn()

    migrations_dir = resolve_migrations_dir()
    if not migrations_dir.exists():
        print("ERRO: diretório de migrations não encontrado")
        sys.exit(1)

    # yoyo's PostgresqlBackend connects through psycopg2 (NOT asyncpg, which yoyo
    # does not support); psycopg2-binary is declared in terreiro/pyproject.toml so
    # the driver is importable. It wants a plain postgresql:// DSN, which is the
    # scheme our DATABASE_URL already uses, so no rewrite is needed.
    subcommand = "mark" if "--mark-only" in sys.argv else "apply"

    # Guard the mark footgun: marking is a one-time legacy-adoption step. Refuse
    # to mark if the retrofit migrations (0018+) are present, unless forced.
    if subcommand == "mark" and "--force-mark-all" not in sys.argv:
        if has_post_legacy_migrations(migrations_dir):
            print(
                "ERRO: 'mark' recusado. Existem migrations 0018+ no diretório, e "
                "marcá-las como aplicadas sem rodar o SQL pularia silenciosamente "
                "a conversão UUID. Rode 'mark' apenas com as migrations legadas "
                "(0001-0017) presentes. Para sobrescrever (não recomendado), use "
                "--force-mark-all."
            )
            sys.exit(1)

    cmd = [
        "yoyo",
        subcommand,
        "--batch",          # never prompt; CI/container friendly
        "--no-config-file",  # ignore any stray yoyo.ini on the search path
        "--database",
        dsn,
        str(migrations_dir),
    ]

    if subcommand == "mark":
        print(
            "Marcando as migrations legadas como aplicadas (sem rodar SQL)..."
        )
    else:
        print("Aplicando migrations pendentes via yoyo...")

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("ERRO: binário 'yoyo' não encontrado no PATH")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"ERRO: yoyo falhou (código {exc.returncode})")
        sys.exit(exc.returncode)

    print("Migrations aplicadas com sucesso")


if __name__ == "__main__":
    main()
