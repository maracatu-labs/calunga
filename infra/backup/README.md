# Postgres backup to Cloudflare R2

Daily `pg_dump` of the Calunga database, uploaded gzipped to a Cloudflare R2
bucket. Runs as the `pg-backup` service in the main `docker-compose.yml`,
sharing the `calunga_internal` network with `db`.

The image is [`eeshugerman/postgres-backup-s3`](https://github.com/eeshugerman/postgres-backup-s3),
an S3-compatible client around `pg_dump`. R2 is S3-compatible so it works
unchanged with `S3_ENDPOINT` pointing to the R2 account endpoint.

## Setup

1. In the Cloudflare dashboard, create an R2 bucket (default name in
   `.env.example`: `maracatu-backups`).
2. Generate an R2 API token under **R2 > Manage API tokens**:
   - Permission: **Object Read & Write**
   - Scope: limited to the backup bucket
3. Fill the host `.env` with:

```
R2_ACCESS_KEY_ID=<from R2 token>
R2_SECRET_ACCESS_KEY=<from R2 token>
R2_BUCKET=maracatu-backups
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
BACKUP_SCHEDULE=@daily
BACKUP_KEEP_DAYS=7
```

4. Start the service:

```bash
docker compose up -d pg-backup
docker compose logs -f pg-backup
```

The first run executes immediately on container start, then follows
`BACKUP_SCHEDULE` (cron expression or `@daily`, `@hourly`, etc).

## Manual backup

```bash
docker compose run --rm pg-backup sh /backup.sh
```

## Restore

1. Find the dump key in R2 (the bucket lists `postgres/calunga-<timestamp>.sql.gz`).
2. Pull it locally, then pipe into the running db:

```bash
# install rclone or use aws cli with the R2 endpoint
aws s3 cp \
  s3://maracatu-backups/postgres/calunga-20260520-030000.sql.gz \
  ./restore.sql.gz \
  --endpoint-url "$R2_ENDPOINT"

gunzip < restore.sql.gz \
  | docker compose exec -T db psql -U maracatu -d maracatu
```

For a full restore over an existing database, `--clean` was passed to
`pg_dump` so the dump drops objects before recreating them.

## Retention

- **Local-side**: `BACKUP_KEEP_DAYS=7` prunes objects older than 7 days on every run.
- **R2-side** (optional): add a bucket lifecycle rule in the Cloudflare
  dashboard to expire after N days, or transition to colder storage.

## Disabling

The `pg-backup` service tries to authenticate to R2 on start. To disable in
development just leave `R2_ACCESS_KEY_ID` empty and run with `--scale
pg-backup=0` or remove the service from the local compose override.
