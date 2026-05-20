# Política de Segurança

Levamos a sério a segurança do Calunga e de quem o usa. Obrigado por nos ajudar a manter o projeto seguro.

## Reportando uma vulnerabilidade

**Não abra issues públicas para vulnerabilidades de segurança.** Em vez disso:

- Use [GitHub Security Advisories](https://github.com/maracatu-labs/calunga/security/advisories/new) (preferencial — privado por padrão), **ou** envie e-mail para **contact@maracatu.org** com:
  - Descrição da vulnerabilidade
  - Passos para reproduzir
  - Impacto potencial
  - Sugestão de correção, se tiver

Vamos confirmar o recebimento em até 72 horas e trabalhar com você para entender e corrigir o problema. Após a correção ser publicada, podemos creditar você na nota de lançamento (se desejar).

## Escopo

Este projeto inclui:

- API REST (`terreiro/`)
- Agente IA com chat (`terreiro/app/agent/`)
- Frontend web (`cortejo/`)
- Pipeline de ingestão (`terreiro/pipeline/`, `terreiro/app/tasks/`)
- Classificadores (`terreiro/app/classifiers/`)

**Fora de escopo:**

- Vulnerabilidades em dependências de terceiros — reporte ao mantenedor original primeiro. Avise-nos se afetar o Calunga diretamente.
- Ataques que dependem de acesso físico ou social engineering contra contribuidores específicos.

## Boas práticas para self-hosters

Se você está rodando o Calunga em produção:

- Sempre defina `JWT_SECRET` com um valor aleatório forte (32+ bytes). Gere com `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- Não exponha as portas do PostgreSQL ou Redis publicamente — use apenas a rede interna do Docker.
- Configure `CORS_ORIGINS` apontando para o domínio público (não use `*`).
- Mantenha `COOKIE_SECURE=true` em produção (já é o padrão).
- Use HTTPS via Caddy (auto-SSL com Let's Encrypt) ou outro proxy reverso à sua escolha.
- Rotacione `GOOGLE_API_KEY`, `TRANSPARENCIA_API_TOKEN` e `RESEND_API_KEY` regularmente.
- Faça backups periódicos do banco (`make backup`).

## Histórico de avisos

Quando publicarmos um aviso de segurança, ele aparecerá em [GitHub Security Advisories](https://github.com/maracatu-labs/calunga/security/advisories).
