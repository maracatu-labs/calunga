"""Magic link delivery via Resend.

Renders a transactional email with HTML + plain text. Both versions share the
same magic-link URL. If Resend is not configured or the API call fails, the
link is logged at WARN level so login is still possible from operator access.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SUBJECT = "Seu link de acesso ao Maracatu"
PREVIEW_TEXT = "Seu link de acesso expira em 15 minutos."

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <title>{subject}</title>
</head>
<body style="margin:0; padding:0; background:#f4f4f4; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <!-- Inbox preview text (hidden) -->
  <div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
    {preview} &#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f4f4; padding:40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:440px; background:#ffffff; border-radius:16px; padding:40px 32px; text-align:center;">
          <tr>
            <td align="center">
              <div style="width:48px; height:48px; background:#000000; color:#ffffff; border-radius:9999px; line-height:48px; font-size:24px; font-weight:700; margin:0 auto 24px;">M</div>
              <h1 style="font-size:20px; font-weight:600; color:#18181b; margin:0 0 8px;">Acesse o Maracatu</h1>
              <p style="font-size:14px; line-height:1.5; color:#71717a; margin:0 0 32px;">
                Clique no botão abaixo para entrar na sua conta.<br>
                Este link expira em 15 minutos.
              </p>
              <a href="{url}" style="display:inline-block; background:#000000; color:#ffffff; padding:14px 32px; border-radius:9999px; text-decoration:none; font-weight:500; font-size:14px;">Entrar no Maracatu</a>
              <p style="font-size:12px; color:#71717a; margin:32px 0 8px;">Ou copie e cole este endereço no navegador:</p>
              <p style="font-size:12px; color:#3f3f46; word-break:break-all; margin:0 0 32px;">
                <a href="{url}" style="color:#3f3f46; text-decoration:underline;">{url}</a>
              </p>
              <hr style="border:none; border-top:1px solid #e4e4e7; margin:0 0 24px;">
              <p style="font-size:12px; color:#a1a1aa; margin:0;">
                Se você não solicitou este acesso, ignore este email.<br>
                Ninguém entrará na sua conta sem clicar no link.
              </p>
            </td>
          </tr>
        </table>
        <p style="font-size:12px; color:#a1a1aa; margin:16px 0 0;">Maracatu — controle social no ritmo do povo.</p>
      </td>
    </tr>
  </table>
</body>
</html>
"""

TEXT_TEMPLATE = """\
Acesse o Maracatu

Clique no link abaixo para entrar na sua conta. Este link expira em 15 minutos.

{url}

Se você não solicitou este acesso, ignore este email. Ninguém entrará na sua conta sem clicar no link.

Maracatu — controle social no ritmo do povo.
"""

async def enviar_magic_link(email: str, token: str) -> None:
    """Send a magic-link email. Falls back to logging the URL on any failure."""
    url = f"{settings.app_url}/auth/verify?token={token}"

    if not settings.resend_api_key:
        logger.warning("MAGIC LINK [no Resend] for %s: %s", email, url)
        return

    html = HTML_TEMPLATE.format(url=url, subject=SUBJECT, preview=PREVIEW_TEXT)
    text = TEXT_TEMPLATE.format(url=url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.email_from,
                    "to": [email],
                    "subject": SUBJECT,
                    "html": html,
                    "text": text,
                    "tags": [{"name": "type", "value": "magic-link"}],
                    "headers": {
                        "X-Entity-Ref-ID": "maracatu-magic-link",
                    },
                },
            )

            if response.status_code in (200, 201):
                logger.info("magic_link_sent email=%s", email)
                return

            logger.error(
                "resend_error status=%s body=%s — falling back to log",
                response.status_code, response.text,
            )
    except Exception as exc:
        logger.error("magic_link_send_failed error=%s — falling back to log", exc)

    logger.warning("MAGIC LINK [fallback] for %s: %s", email, url)
