"""Aplica migrations SQL no banco de dados."""

import asyncio
import sys
from pathlib import Path

import asyncpg

async def main():
    dsn = sys.argv[1] if len(sys.argv) > 1 else "postgresql://maracatu:changeme@db:5432/maracatu"

    migrations_dir = Path("/app/migrations")
    if not migrations_dir.exists():
        migrations_dir = Path(__file__).resolve().parent.parent / "terreiro" / "migrations"

    if not migrations_dir.exists():
        print(f"ERRO: diretório de migrations não encontrado")
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
