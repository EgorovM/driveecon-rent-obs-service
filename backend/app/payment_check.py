"""Проверка PDF-квитанции об оплате аренды через LLM (OpenRouter).

Извлекаем текст из PDF, отдаём его модели вместе с ожидаемыми параметрами
платежа (сумма, период, объект) и просим вынести вердикт. Если квитанция не
соответствует ожиданиям — возвращаем понятную причину, которую показываем
арендатору и не отмечаем период оплаченным.
"""

import io
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from pypdf import PdfReader

from app.config import settings


@dataclass
class VerifyResult:
    ok: bool
    reason: str


class PdfExtractError(Exception):
    """PDF не читается или не содержит текста."""


def extract_pdf_text(data: bytes, max_chars: int = 12000) -> str:
    """Вытаскивает текстовый слой из PDF. Бросает PdfExtractError, если пусто."""
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as e:  # noqa: BLE001 — любая ошибка парсинга = битый PDF
        raise PdfExtractError("Не удалось прочитать PDF-файл") from e

    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    text = "\n".join(parts).strip()
    if not text:
        raise PdfExtractError(
            "В PDF не найден текст. Прикрепите электронную квитанцию из банка "
            "(не фотографию/скан)."
        )
    return text[:max_chars]


_SYSTEM_PROMPT = (
    "Ты — помощник владельца коммерческой недвижимости. Тебе дают текст, "
    "извлечённый из банковской квитанции/чека об оплате, и ожидаемые параметры "
    "платежа за аренду. Определи, действительно ли это квитанция об успешном "
    "переводе/оплате и совпадают ли сумма и получатель/назначение с ожидаемыми. "
    "Небольшие расхождения в форматировании допустимы. Сумма должна совпадать "
    "(допускается, что в квитанции сумма равна или больше ожидаемой). Если это не "
    "квитанция об оплате, платёж не выполнен, или сумма меньше ожидаемой — это "
    "несоответствие. Ответь СТРОГО одним JSON-объектом без markdown: "
    '{"ok": true|false, "reason": "краткое объяснение на русском"}. '
    "В reason при ok=false понятно укажи, что именно не так."
)


def _build_user_prompt(pdf_text: str, *, amount_due: int, period_label: str,
                       property_name: str, tenant_name: str) -> str:
    return (
        "Ожидаемые параметры платежа:\n"
        f"- Объект аренды: {property_name}\n"
        f"- Арендатор (плательщик): {tenant_name}\n"
        f"- Период: {period_label}\n"
        f"- Сумма к оплате: {amount_due} руб.\n\n"
        "Текст из прикреплённого PDF (банковская квитанция):\n"
        "<<<\n"
        f"{pdf_text}\n"
        ">>>\n\n"
        "Это корректная квитанция об оплате на нужную сумму? Ответь JSON."
    )


def _parse_verdict(content: str) -> VerifyResult:
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return VerifyResult(False, "Не удалось проверить квитанцию автоматически, попробуйте ещё раз.")
    ok = bool(data.get("ok"))
    reason = str(data.get("reason") or "").strip()
    if not reason:
        reason = "Оплата подтверждена." if ok else "Квитанция не соответствует ожидаемому платежу."
    return VerifyResult(ok, reason)


def verify_payment(
    pdf_text: str,
    *,
    amount_due: int,
    period_label: str,
    property_name: str,
    tenant_name: str,
) -> VerifyResult:
    """Спрашивает LLM, корректна ли квитанция. Бросает RuntimeError при сбое API."""
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY не задан в окружении")

    payload = json.dumps(
        {
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        pdf_text,
                        amount_due=amount_due,
                        period_label=period_label,
                        property_name=property_name,
                        tenant_name=tenant_name,
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 300,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Drivee/1.0",
            "HTTP-Referer": settings.frontend_url,
            "X-Title": "Drivee",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.smtp_timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"OpenRouter API {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenRouter API недоступен: {e.reason}") from e

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError("OpenRouter вернул неожиданный ответ") from e

    return _parse_verdict(content)
