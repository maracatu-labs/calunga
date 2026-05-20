"""Envio de magic link por email via Resend."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, system-ui, sans-serif; background: #f4f4f4; padding: 40px 20px;">
  <div style="max-width: 420px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; text-align: center;">
    <div style="width: 48px; height: 48px; background: black; color: white; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; margin-bottom: 24px;">M</div>
    <h1 style="font-size: 20px; font-weight: 600; color: #18181b; margin-bottom: 8px;">Acesse o Maracatu</h1>
    <p style="font-size: 14px; color: #71717a; margin-bottom: 32px;">Clique no botão abaixo para acessar sua conta. Este link expira em 15 minutos.</p>
    <a href="{url}" style="display: inline-block; background: black; color: white; padding: 14px 32px; border-radius: 999px; text-decoration: none; font-weight: 500; font-size: 14px;">Acessar o Maracatu</a>
    <p style="font-size: 12px; color: #a1a1aa; margin-top: 32px;">Se você não solicitou este acesso, ignore este email.</p>
  </div>
</body>
</html>
"""

async def enviar_magic_link(email: str, token: str) -> None:
    """Envia email com magic link. Se falhar, loga o link no console (não bloqueia o login)."""
    url = f"{settings.app_url}/auth/verify?token={token}"

    if not settings.resend_api_key:
        logger.warning("MAGIC LINK [sem Resend] para %s: %s", email, url)
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.email_from,
                    "to": [email],
                    "subject": "Seu acesso ao Maracatu",
                    "html": EMAIL_TEMPLATE.format(url=url),
                },
            )

            if response.status_code in (200, 201):
                logger.info("Magic link enviado para %s via Resend", email)
                return

            logger.error("Resend retornou %s: %s — logando link no console", response.status_code, response.text)
    except Exception as exc:
        logger.error("Erro ao enviar email: %s — logando link no console", exc)

    logger.warning("MAGIC LINK [fallback] para %s: %s", email, url)
