from __future__ import annotations

import json
from typing import Any

import httpx

from .config import get_settings


def compact_page(page: dict, max_chars: int = 3500) -> dict:
    text = page.get("markdown") or page.get("text") or ""
    return {
        "url": page.get("url"),
        "depth": page.get("depth"),
        "title": page.get("title"),
        "description": page.get("description"),
        "content": str(text)[:max_chars],
        "links": (page.get("links") or [])[:20],
    }


def fallback_analysis(pages: list[dict], reason: str, instruction: str | None = None) -> dict:
    page_summaries = []
    for page in pages[:12]:
        text = str(page.get("markdown") or page.get("text") or "").replace("\n", " ").strip()
        page_summaries.append(
            {
                "title": page.get("title") or "Başlıksız sayfa",
                "url": page.get("url"),
                "summary": text[:360] or page.get("description") or "Bu sayfada anlamlandırılacak metin sınırlı.",
                "important_items": [],
            }
        )

    titles = [page.get("title") for page in pages if page.get("title")]
    return {
        "enabled": False,
        "provider": "fallback",
        "reason": reason,
        "prompt": instruction,
        "summary": (
            "LLM anahtarı yapılandırılmadığı için otomatik yapısal özet üretildi. "
            "Z.ai/OpenAI anahtarı eklenince sonuç kullanıcının verdiği prompt isteğine göre üretilecek."
        ),
        "key_points": titles[:6] or ["Sayfalar scrape edildi, fakat anlamlı başlık sayısı sınırlı."],
        "opportunities": [],
        "entities": [],
        "recommended_actions": ["Z_AI_API_KEY env değerini ekle", "Crawl sonucunu tekrar çalıştır", "Gerekirse dynamic mode ile daha zengin içerik çek"],
        "page_summaries": page_summaries,
    }


def extract_response_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    chunks: list[str] = []
    for item in data.get("output") or []:
        for content in item.get("content") or []:
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


def parse_json_response(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def z_ai_key() -> str | None:
    settings = get_settings()
    return settings.z_ai_api_key or settings.zai_api_key


async def call_zai_chat(system: str, corpus: dict[str, Any]) -> dict:
    settings = get_settings()
    base_url = settings.zai_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {z_ai_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.zai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(corpus, ensure_ascii=False)},
                ],
                "thinking": {"type": "enabled"},
                "temperature": 0.2,
                "max_tokens": 2400,
            },
        )
        response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = parse_json_response(content)
    parsed["enabled"] = True
    parsed["provider"] = "zai"
    parsed["model"] = settings.zai_model
    return parsed


async def call_openai_responses(system: str, corpus: dict[str, Any]) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "input": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(corpus, ensure_ascii=False)},
                ],
                "max_output_tokens": 2400,
            },
        )
        response.raise_for_status()
    text = extract_response_text(response.json()).strip()
    parsed = json.loads(text)
    parsed["enabled"] = True
    parsed["provider"] = "openai"
    parsed["model"] = settings.openai_model
    return parsed


async def analyze_crawl(pages: list[dict], root_url: str, instruction: str | None = None) -> dict:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "zai" and not z_ai_key():
        return fallback_analysis(pages, "Z_AI_API_KEY is not configured", instruction)
    if provider == "openai" and not settings.openai_api_key:
        return fallback_analysis(pages, "OPENAI_API_KEY is not configured", instruction)

    corpus = {
        "root_url": root_url,
        "pages": [compact_page(page) for page in pages[:20]],
        "instruction": instruction or "Site içeriğini Türkçe olarak anlamlandır. Fırsat, ihale, başvuru, önemli tarih, doküman ve aksiyonları çıkar.",
    }
    system = (
        "Sen bir web veri analisti ve araştırma asistanısın. Scrape edilmiş sayfaları ham link listesi gibi değil, "
        "insanın karar verebileceği yapılandırılmış bilgi olarak özetle. Türkçe yaz. "
        "Sadece geçerli JSON döndür: summary, key_points, opportunities, entities, recommended_actions, page_summaries alanları olsun."
    )
    try:
        if provider == "zai":
            parsed = await call_zai_chat(system, corpus)
        elif provider == "openai":
            parsed = await call_openai_responses(system, corpus)
        else:
            return fallback_analysis(pages, f"Unsupported LLM_PROVIDER: {settings.llm_provider}", instruction)
        parsed["prompt"] = instruction
        return parsed
    except Exception as exc:
        fallback = fallback_analysis(pages, f"LLM analysis failed: {exc}", instruction)
        fallback["enabled"] = False
        fallback["provider"] = "fallback_after_error"
        return fallback
