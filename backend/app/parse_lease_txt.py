import re
from datetime import date, datetime

from pydantic import EmailStr, TypeAdapter, ValidationError


def _parse_date(s: str) -> date | None:
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_lease_txt(content: str) -> dict:
    """
    Ожидает строки вида: ФИО / Email / даты начала и окончания.
    Гибкий разбор ключевых слов на русском и английском.
    """
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    data: dict = {}
    for line in lines:
        low = line.lower()
        if ":" in line:
            key, val = line.split(":", 1)
            key, val = key.strip().lower(), val.strip()
        elif "=" in line:
            key, val = line.split("=", 1)
            key, val = key.strip().lower(), val.strip()
        else:
            continue

        if any(x in key for x in ("фио", "name", "tenant")):
            data["tenant_name"] = val
        elif "email" in key or "почт" in key:
            data["tenant_email"] = val
        elif any(x in key for x in ("начал", "start", "от", "дата аренды")):
            d = _parse_date(val)
            if d:
                data["rent_start"] = d
        elif any(x in key for x in ("оконч", "конец", "end", "срок", "до")):
            d = _parse_date(val)
            if d:
                data["rent_end"] = d

    # Fallback: первое похожее на email (явно включаем _ в локальной части, без двусмысленных диапазонов в [])
    email_pattern = r"[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    if "tenant_email" not in data:
        m = re.search(email_pattern, content, re.IGNORECASE)
        if m:
            data["tenant_email"] = m.group(0)

    if "tenant_name" not in data:
        for line in lines:
            if "@" not in line and len(line) > 3 and not re.match(r"^\d", line):
                data["tenant_name"] = line.split(":", 1)[-1].strip()
                break

    dates_found: list[date] = []
    for m in re.finditer(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{2}-\d{2}", content):
        d = _parse_date(m.group(0))
        if d:
            dates_found.append(d)
    if len(dates_found) >= 2:
        data.setdefault("rent_start", min(dates_found))
        data.setdefault("rent_end", max(dates_found))
    elif len(dates_found) == 1:
        data.setdefault("rent_end", dates_found[0])

    missing = [k for k in ("tenant_name", "tenant_email", "rent_start", "rent_end") if k not in data]
    if missing:
        raise ValueError(f"Не удалось разобрать поля: {', '.join(missing)}")

    try:
        TypeAdapter(EmailStr).validate_python(data["tenant_email"])
    except ValidationError as e:
        raise ValueError(f"Некорректный email: {e}") from e

    return {
        "tenant_name": str(data["tenant_name"]),
        "tenant_email": str(data["tenant_email"]),
        "rent_start": data["rent_start"],
        "rent_end": data["rent_end"],
    }
