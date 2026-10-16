"""indices.py - index projection: a series' annual history -> a yearly growth rate -> index levels.

Levels are relative to the base year (level(base_year) = 1.0) and compound with the method's rate:
    level(y) = (1 + r) ** (y - base_year)
'path' gives explicit levels instead. Pure functions; no files.

History = tuple of (year, value) sorted by year (a tuple so rate_for can be cached).
Window N = the last N annual POINTS (spec 4.1: 3 points -> 2 yearly changes).
"""

from functools import lru_cache


def _yoy(h: tuple, n: int) -> list[float]:
    """Year-on-year changes among the last n points (n points -> n-1 changes)."""
    ys = [v for _, v in h[-n:]]
    return [b / a - 1 for a, b in zip(ys, ys[1:]) if a]


def mean_yoy(h: tuple, years: int, **_) -> float:
    """Average yearly change among the last `years` points."""
    r = _yoy(h, years)
    if len(h) < years or not r:
        raise ValueError(f"mean_yoy {years}: history too short ({len(h)} points)")
    return sum(r) / len(r)


def cagr(h: tuple, years: int, **_) -> float:
    """Compound growth between the first and last of the last `years` points."""
    if len(h) < years or years < 2:
        raise ValueError(f"cagr {years}: history too short ({len(h)} points)")
    a, b = h[-years][1], h[-1][1]
    return (b / a) ** (1 / (years - 1)) - 1


def trend(h: tuple, years: int, **_) -> float:
    """Least-squares slope over the last `years` points, divided by the last value."""
    pts = h[-years:]
    if len(pts) < 2:
        raise ValueError(f"trend {years}: history too short ({len(h)} points)")
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return slope / ys[-1]


def fixed(h: tuple, rate: float, **_) -> float:
    """A stated yearly rate (history ignored)."""
    return float(rate)


METHODS = {
    "fixed": {"label": "fixed rate per year", "fn": fixed},
    "mean_yoy": {"label": "average of the last N yearly changes", "fn": mean_yoy},
    "cagr": {"label": "compound growth over the last N years", "fn": cagr},
    "trend": {"label": "linear trend over the last N years (slope / last value)", "fn": trend},
    "path": {"label": "explicit yearly levels", "fn": None},
}


@lru_cache(maxsize=4096)
def rate_for(history: tuple, method: str, rate: float | None, years: int | None) -> float:
    if method not in METHODS or METHODS[method]["fn"] is None:
        raise ValueError(f"no rate for method '{method}'")
    return METHODS[method]["fn"](history, rate=rate, years=years)


def levels(method: str, history: tuple, base_year: int, years: range, *, rate: float | None = None,
           window: int | None = None, path: dict[int, float] | None = None) -> dict[int, float]:
    """{year: level} with level(base_year) = 1.0."""
    if method == "path":
        return {y: float(path[y]) for y in years}
    r = rate_for(history, method, rate, window)
    return {y: (1 + r) ** (y - base_year) for y in years}
