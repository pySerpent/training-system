"""Общие вспомогательные функции: округление и вывод чисел."""
from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value: float, digits: int = 1) -> float:
    """Округление «половина вверх» (23,35 -> 23,4), а не банковское, как у round()."""
    quant = Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def fmt_num(value) -> str:
    """Число для показа пользователю: десятичная запятая, без лишнего «,0»."""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value}".replace(".", ",")
    return str(value)


def fmt_pct(value) -> str:
    """Процент с запятой: 88,8 %."""
    return f"{fmt_num(value)} %"
