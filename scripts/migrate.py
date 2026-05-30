"""Aplica migrations SQL no banco de dados."""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

async def main():
    # Resolve the DSN from (1) an explicit argv override, (2) DATABASE_URL from
    # the environment (how every container, prod included, gets its real
    # credentials), and only then (3) the local-dev default. The default must
    # never be relied on in prod: the real password lives in DATABASE_URL.
    dsn = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("DATABASE_URL", "postgresql://maracatu:changeme@db:5432/maracatu")
    )

    migrations_dir = Path("/app/migrations")
    if not migrations_dir.exists():
        migrations_dir = Path(__file__).resolve().parent.parent / "terreiro" / "migrations"

    if not migrations_dir.exists():
        print("ERRO: diretório de migrations não encontrado")
        sys.exit(1)

    sql_files = sorted(f for f in migrations_dir.glob("*.sql") if ".rollback." not in f.name)
    if not sql_files:
        print(f"ERRO: nenhum arquivo .sql encontrado em {migrations_dir}")
        sys.exit(1)

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    try:
        for sql_file in sql_files:
            print(f"Aplicando {sql_file.name}...")
            sql = sql_file.read_text()
            await pool.execute(sql)
        print("Migrations aplicadas com sucesso")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
