"""A transparent, bounded public-interest projection. Never a price or ROI prediction."""

import math
import statistics
from datetime import date, timedelta
from itertools import pairwise

from app.schemas.development import SearchMomentum
from app.schemas.forecast import ForecastPoint, TrendForecast

NOTE = (
    "Linear continuation of the last 26 weekly public-interest observations, bounded to 0-100. "
    "Bands show historical fit and holdout error, not calibrated confidence intervals. "
    "Search interest is not demand, price appreciation or an investment return. "
    "Seasonality and structural changes are not modelled. Projection is anchored to this run."
)


def _fit(values: list[float]) -> tuple[float, float]:
    center = (len(values) - 1) / 2
    mean = statistics.mean(values)
    slope = sum((i - center) * (v - mean) for i, v in enumerate(values)) / sum(
        (i - center) ** 2 for i in range(len(values))
    )
    return mean - slope * center, slope


def project_interest(signal: SearchMomentum, as_of: date) -> TrendForecast:
    history = sorted(signal.history, key=lambda p: p.week)[-26:]
    result = TrendForecast(
        kind=signal.kind,
        status="unavailable",
        as_of=as_of,
        observations=len(history),
        source=signal.source,
        note=NOTE,
    )
    if (
        signal.unit != "relative_interest_0_100"
        or signal.source is None
        or len(history) < 26
        or len({p.week for p in history}) != 26
        or not 0 <= (as_of - history[-1].week).days <= 21
        or any(not math.isfinite(p.value) or not 0 <= p.value <= 100 for p in history)
        or any((b.week - a.week).days != 7 for a, b in pairwise(history))
        or sum(p.value > 0 for p in history) < 8
    ):
        result.note = (
            "Needs 26 consecutive, recent, sourced, non-sparse public weekly observations. " + NOTE
        )
        return result
    values = [p.value for p in history]
    a, b = _fit(values[:-4])
    mae = statistics.mean(abs(v - (a + b * i)) for i, v in enumerate(values[-4:], 22))
    a, b = _fit(values)
    error = max(mae, statistics.mean(abs(v - (a + b * i)) for i, v in enumerate(values)))

    def clamp(value: float) -> float:
        return round(min(100, max(0, value)), 2)

    result.status = "projected"
    result.holdout_mae = round(mae, 2)
    for lead in (4, 12):
        value = a + b * (25 + lead)
        width = max(1, error * math.sqrt(1 + lead / 4))
        result.points.append(
            ForecastPoint(
                week=history[-1].week + timedelta(weeks=lead),
                value=clamp(value),
                lower=clamp(value - width),
                upper=clamp(value + width),
            )
        )
    return result
