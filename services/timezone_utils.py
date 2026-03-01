"""
timezone_utils.py — Utilidades de zona horaria para LogiPartVE Pro
Venezuela usa UTC-4 (hora fija, sin cambio de horario de verano).
"""

from datetime import datetime, timezone, timedelta

# Zona horaria de Venezuela: UTC-4 (fija, sin DST)
TZ_CARACAS = timezone(timedelta(hours=-4))


def now_caracas() -> datetime:
    """Devuelve la fecha y hora actual en la zona horaria de Caracas (UTC-4)."""
    return datetime.now(tz=TZ_CARACAS)


def now_caracas_naive() -> datetime:
    """
    Devuelve la fecha y hora actual en Caracas sin información de zona horaria
    (naive datetime), útil para guardar en SQLite o comparaciones simples.
    """
    return datetime.now(tz=TZ_CARACAS).replace(tzinfo=None)


def utc_to_caracas(dt: datetime) -> datetime:
    """
    Convierte un datetime UTC (con o sin tzinfo) a la hora de Caracas.
    Si el datetime no tiene tzinfo, se asume que es UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_CARACAS)


def format_caracas(dt: datetime, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """
    Formatea un datetime convirtiéndolo primero a hora de Caracas.
    Si dt es None o inválido, devuelve cadena vacía.
    """
    if dt is None:
        return ""
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return utc_to_caracas(dt).strftime(fmt)
    except Exception:
        return str(dt)
