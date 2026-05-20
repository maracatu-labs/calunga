from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "maracatu",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    beat_schedule={
        "ingestao-camara-deputados": {
            "task": "app.tasks.ingestao.ingestao_camara_deputados",
            "schedule": crontab(hour=3, minute=0),
        },
        "ingestao-camara-despesas": {
            "task": "app.tasks.ingestao.ingestao_camara_despesas",
            "schedule": crontab(hour=4, minute=0),
        },
        "ingestao-senado": {
            "task": "app.tasks.ingestao.ingestao_senado",
            "schedule": crontab(hour=4, minute=30),
        },
        "analise-suspeitas": {
            "task": "app.tasks.ingestao.analise_suspeitas",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)
