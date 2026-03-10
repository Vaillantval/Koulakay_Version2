"""
Service de taux de change — KouLakay
Fournit les taux live avec cache 1h via open.er-api.com (gratuit, sans clé API).
"""
import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "koulakay_fx_to_htg_"
_CACHE_TIMEOUT = 3600  # 1 heure
_API_BASE = "https://open.er-api.com/v6/latest"


def get_htg_rate(from_currency: str) -> float | None:
    """
    Retourne combien de HTG = 1 unité de `from_currency`.
    Ex: get_htg_rate('USD') → 132.5  (1 USD = 132.5 HTG)

    - Utilise le cache Django (1h).
    - Retourne None si l'API est injoignable.
    """
    from_currency = from_currency.upper()
    if from_currency == "HTG":
        return 1.0

    cache_key = _CACHE_PREFIX + from_currency
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(f"{_API_BASE}/{from_currency}", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") == "success":
            rate = data.get("rates", {}).get("HTG")
            if rate:
                cache.set(cache_key, float(rate), _CACHE_TIMEOUT)
                return float(rate)
    except Exception as exc:
        logger.warning("[KouLakay] Taux de change indisponible (%s→HTG): %s", from_currency, exc)

    return None


def convert_to_htg(amount, from_currency: str) -> float | None:
    """
    Convertit `amount` en HTG depuis `from_currency`.
    Retourne None si le taux est indisponible.
    """
    rate = get_htg_rate(from_currency)
    if rate is None:
        return None
    return round(float(amount) * rate, 2)


def convert_from_htg(amount_htg, to_currency: str) -> float | None:
    """
    Convertit `amount_htg` (en HTG) vers `to_currency`.
    Retourne None si le taux est indisponible.
    """
    to_currency = to_currency.upper()
    if to_currency == "HTG":
        return round(float(amount_htg), 2)

    rate = get_htg_rate(to_currency)  # HTG per 1 to_currency
    if rate is None or rate == 0:
        return None
    return round(float(amount_htg) / rate, 2)
