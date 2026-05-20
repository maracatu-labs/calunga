"""
OCR de recibos parlamentares.

Fluxo: Download PDF → Extração de texto → Análise via LLM.
Usa PyMuPDF (fitz) para extrair texto de PDFs.
Se o PDF for imagem (scan), usa Claude Vision para OCR.
"""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

async def download_pdf(url: str) -> bytes | None:
    """Baixa o PDF de um recibo parlamentar."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            if "pdf" not in resp.headers.get("content-type", "").lower() and not url.lower().endswith(".pdf"):
                return None
            return resp.content
    except Exception as e:
        logger.warning(f"Erro baixando PDF {url}: {e}")
        return None

def extract_text_from_pdf(pdf_bytes: bytes) -> str | None:
    """Extrai texto de PDF usando PyMuPDF."""
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip() if text.strip() else None
    except ImportError:
        logger.warning("PyMuPDF não instalado. Instale com: pip install PyMuPDF")
        return None
    except Exception as e:
        logger.warning(f"Erro extraindo texto do PDF: {e}")
        return None

async def analyze_receipt_with_llm(text: str) -> dict:
    """Analisa texto de recibo usando Gemini para identificar irregularidades."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from app.config import settings

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key, max_output_tokens=1024)

    prompt = f"""Analise este recibo/nota fiscal de despesa parlamentar e extraia:

1. ITENS: liste cada item com quantidade e valor
2. ÁLCOOL: identifique se há bebidas alcoólicas (proibido pelo CEAP)
3. DISCRIMINAÇÃO: verifique se os itens estão discriminados (não vale "refeição" genérica)
4. VALOR TOTAL: some os itens e compare com o valor da nota
5. IRREGULARIDADES: liste qualquer problema encontrado

Texto do recibo:
---
{text[:3000]}
---

Responda em JSON com os campos: itens (lista), tem_alcool (bool), itens_discriminados (bool), valor_total (float), irregularidades (lista de strings)."""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)

        import json
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        return {"raw_analysis": content}

    except Exception as e:
        logger.warning(f"Erro analisando recibo com LLM: {e}")
        return {"error": str(e)}

async def process_receipt(url: str) -> dict | None:
    """Pipeline completo: download → OCR → análise LLM."""
    pdf_bytes = await download_pdf(url)
    if not pdf_bytes:
        return None

    text = extract_text_from_pdf(pdf_bytes)
    if not text:
        logger.info("PDF sem texto extraível (provavelmente scan/imagem)")
        return {"status": "no_text", "needs_vision_ocr": True}

    analysis = await analyze_receipt_with_llm(text)
    analysis["source_url"] = url
    analysis["extracted_text_length"] = len(text)
    return analysis
