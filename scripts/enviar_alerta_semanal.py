"""
Envia resumo semanal de suspeitas por e-mail.

Uso:
    python scripts/enviar_alerta_semanal.py
    python scripts/enviar_alerta_semanal.py --email fulano@email.com
"""

import argparse
import asyncio
import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terreiro"))

import asyncpg

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def get_resumo_semanal(pool: asyncpg.Pool) -> dict:
    """Busca resumo de suspeitas da última semana."""
    total = await pool.fetchval(
        "SELECT COUNT(*) FROM suspeitas WHERE created_at >= NOW() - INTERVAL '7 days'"
    )

    por_classificador = await pool.fetch(
        """
        SELECT classificador, COUNT(*) AS total
        FROM suspeitas WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY classificador ORDER BY total DESC
        """
    )

    top_parlamentares = await pool.fetch(
        """
        SELECT p.nome, p.partido, p.uf, COUNT(*) AS total_suspeitas
        FROM suspeitas s
        JOIN despesas d ON s.despesa_id = d.id
        JOIN parlamentares p ON d.parlamentar_id = p.id
        WHERE s.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY p.nome, p.partido, p.uf
        ORDER BY total_suspeitas DESC
        LIMIT 10
        """
    )

    return {
        "total": total,
        "por_classificador": [dict(r) for r in por_classificador],
        "top_parlamentares": [dict(r) for r in top_parlamentares],
    }

def build_html(resumo: dict) -> str:
    """Gera HTML do e-mail."""
    classificadores_html = ""
    for c in resumo["por_classificador"]:
        classificadores_html += f"<tr><td>{c['classificador']}</td><td>{c['total']}</td></tr>"

    parlamentares_html = ""
    for p in resumo["top_parlamentares"]:
        parlamentares_html += f"<tr><td>{p['nome']}</td><td>{p['partido']}/{p['uf']}</td><td>{p['total_suspeitas']}</td></tr>"

    return f"""
    <html>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Maracatu — Resumo Semanal de Suspeitas</h2>
        <p>Total de suspeitas na última semana: <strong>{resumo['total']}</strong></p>

        <h3>Por tipo de irregularidade</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr><th>Classificador</th><th>Quantidade</th></tr>
            {classificadores_html}
        </table>

        <h3>Parlamentares com mais suspeitas</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr><th>Parlamentar</th><th>Partido/UF</th><th>Suspeitas</th></tr>
            {parlamentares_html}
        </table>

        <p style="color: #666; font-size: 12px; margin-top: 20px;">
            Gerado automaticamente pelo Maracatu — Controle social dos gastos públicos
        </p>
    </body>
    </html>
    """

def send_email(to: str, subject: str, html: str):
    """Envia e-mail via SMTP."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_email = os.environ.get("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP não configurado (SMTP_USER/SMTP_PASS). Salvando HTML localmente.")
        Path("/tmp/alerta_semanal.html").write_text(html)
        logger.info("HTML salvo em /tmp/alerta_semanal.html")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, [to], msg.as_string())

    logger.info(f"E-mail enviado para {to}")

async def main():
    parser = argparse.ArgumentParser(description="Enviar alerta semanal de suspeitas")
    parser.add_argument("--email", default=os.environ.get("ALERT_EMAIL", ""), help="E-mail do destinatário")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=2)

    try:
        resumo = await get_resumo_semanal(pool)
        logger.info(f"Resumo: {resumo['total']} suspeitas na semana")

        if resumo["total"] == 0:
            logger.info("Nenhuma suspeita nova — não enviando e-mail")
            return

        html = build_html(resumo)
        subject = f"Maracatu — {resumo['total']} suspeitas detectadas esta semana"

        if args.email:
            send_email(args.email, subject, html)
        else:
            Path("/tmp/alerta_semanal.html").write_text(html)
            logger.info("E-mail não configurado. HTML salvo em /tmp/alerta_semanal.html")

    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
