"""fetchers.py - read a published index series from an OFFICIAL web source. Plain
functions, no agent.

Nothing per-index is hard-coded. The index_resolver agent finds the official URL
(web search or its
own knowledge); this file then:
1. checks the URL is an OFFICIAL publisher (government / statistics office /
regulator domain) - news, blogs and aggregators are refused;
2. downloads it and turns any format (xls, xlsx, csv, html table, pdf, zip) into
plain text;
3. has the model TRANSCRIBE the printed annual values for the one series (it
copies, never computes);
4. validates the numbers (enough years, positive, no impossible jumps) and
FREEZES them to disk with
the URL, download time and content hash - so every value is traceable to the
official file.
"""

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import requests

from .settings import TOOL_TIMEOUT_S, http_options, model_for

MAX_TEXT_CHARS = 120_000   # what the model sees of one downloaded file
MIN_YEARS = 3              # a usable annual history
MAX_YOY_JUMP = 1.0         # |year-on-year change| above 100 % = misread or wrong series
DATA_WORDS = (
    "data", "index", "indices", "series", "statistic", "download", "table",
    "price", "wage", "tariff", "number",
)
DATA_LINK_TERMS = (
    "index", "data", "series", "statistic", "historical", "archive",
    "download", "annual", "calendar", "year",
)
DATA_FILE_EXTENSIONS = {".xls", ".xlsx", ".csv", ".zip", ".pdf"}

# Official publishers: government, statistics, central bank, regulator domains
# (any country).
OFFICIAL_SUFFIXES = (".gov", ".gov.in", ".nic.in", ".gov.uk", ".gouv.fr", ".go.jp", ".gc.ca", ".gov.au",
                     ".europa.eu", ".bund.de", ".admin.ch", ".gob.mx", ".gov.br",
                     ".gov.cn", ".gov.sg",
                     ".mil", ".int")
OFFICIAL_HOSTS = ("rbi.org.in", "mospigov.in", "bls.gov", "bea.gov", "eia.gov", "ons.gov.uk",
                  "stat.go.jp", "boj.or.jp", "e-stat.go.jp", "destatis.de", "insee.fr", "istat.it",
                  "ine.es", "cbs.nl", "statcan.gc.ca", "abs.gov.au", "ecb.europa.eu", "imf.org",
                  "worldbank.org", "oecd.org")
# Electricity regulatory commissions ('<state>erc.org',
# 'cercind.gov.in', ...): official tariff publishers.
OFFICIAL_PATTERNS = (r"(^|\.)[a-z]*erc(india)?\.(org|gov)(\.[a-z]{2})?$", r"(^|\.)cercind\.gov\.in$")

REFUSED_HINTS = ("news", "blog", "wiki", "medium.com", "investing.com", "tradingeconomics", "ceicdata",
                 "statista", "macrotrends", "economictimes", "livemint",
                 "moneycontrol", "reddit")


# -----------------------------------------------------------------------------
# 1. official source check
# -----------------------------------------------------------------------------
def official_domain(url: str) -> tuple[bool, str]:
    """(is official, why). Government / statistics / central-bank / regulator hosts only."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if not host:
        return False, "not a URL"
    if any(h in host for h in REFUSED_HINTS):
        return False, f"{host} is a news / blog / aggregator site, not the publisher"
    if (
        host.endswith(OFFICIAL_SUFFIXES)
        or any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS)
        or any(re.search(p, host) for p in OFFICIAL_PATTERNS)
    ):
        return True, f"{host} is an official publisher domain"
    return False, f"{host} is not a recognised official publisher domain"


def _without_fragment(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit(parsed._replace(fragment=""))


def data_links(html: str | bytes, page_url: str) -> list[tuple[str, str]]:
    """Find official data pages and files linked from an official HTML page."""
    from bs4 import BeautifulSoup

    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    page = _without_fragment(page_url)
    page_host = (urlparse(page).hostname or "").lower().removeprefix("www.")
    pages: list[tuple[str, str]] = []
    files: list[tuple[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("mailto:", "javascript:", "tel:")):
            continue
        target = _without_fragment(urljoin(page, href))
        if target == page:
            continue
        is_official, _ = official_domain(target)
        if not is_official:
            continue

        parsed = urlparse(target)
        path = parsed.path.lower()
        host = (parsed.hostname or "").lower().removeprefix("www.")
        suffix = Path(path).suffix
        text = " ".join(anchor.stripped_strings).strip()
        if not text:
            text = path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")

        if suffix in DATA_FILE_EXTENSIONS:
            files.append((text, target))
        elif host == page_host and any(
            word in f"{text} {path}".lower() for word in DATA_WORDS
        ):
            pages.append((text, target))

    result = []
    seen = set()
    for link in pages + files:
        if link[1] not in seen:
            seen.add(link[1])
            result.append(link)
    return result


def rank_links(links: list[tuple[str, str]], meaning: str) -> list[tuple[str, str]]:
    """Rank official data links by series relevance, data-history hints, and recency."""
    meaning_words = set(re.findall(r"[a-z]{3,}", meaning.lower()))
    current_year = datetime.now().year

    def score(link: tuple[str, str]) -> int:
        text, url = link
        path = urlparse(url).path.lower()
        description = f"{text} {url}".lower()
        description_words = set(re.findall(r"[a-z]{3,}", description))
        total = len(meaning_words & description_words)
        searchable = f"{text} {path}".lower()
        total += sum(searchable.count(term) for term in DATA_LINK_TERMS)
        if Path(path).suffix in {".xls", ".xlsx", ".csv"}:
            total += 2
        years = [int(year) for year in re.findall(r"\b\d{4}\b", description)]
        if any(year >= current_year - 15 for year in years):
            total += 2
        elif years:
            total -= 3
        return total

    return sorted(links, key=score, reverse=True)


_NUMBER_PATTERN = re.compile(
    r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w.])"
)


def numbers_in(text: str) -> set[float]:
    """Return printed numeric values, rounded to four decimal places."""
    return {
        round(float(match.replace(",", "")), 4)
        for match in _NUMBER_PATTERN.findall(text)
    }


def not_in_file(values: list[dict], text: str) -> list[dict]:
    """Return transcribed values that do not appear numerically in the source text."""
    printed = numbers_in(text)
    missing = []
    for item in values:
        try:
            value = round(float(item["value"]), 4)
        except (KeyError, TypeError, ValueError):
            missing.append(item)
            continue
        if value not in printed:
            missing.append(item)
    return missing


# -----------------------------------------------------------------------------
# 2. download + any format -> text
# -----------------------------------------------------------------------------
class _SystemTrust(requests.adapters.HTTPAdapter):
    """Verify certificates with the OS trust store (macOS keychain / Windows / Linux CA store) instead
    of certifi's bundle. Government sites often send cross-signed chains (labourbureau.gov.in:
    eMudhra + the old Comodo 'AAA Certificate Services' root) that browsers and curl accept but
    certifi + OpenSSL reject as 'self-signed certificate in certificate chain'. Still full
    verification - never verify=False."""

    def init_poolmanager(self, *args, **kwargs):
        import ssl

        import truststore

        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        super().init_poolmanager(*args, **kwargs)


@cache
def _session() -> requests.Session:
    session = requests.Session()
    try:
        import truststore  # noqa: F401
        session.mount("https://", _SystemTrust())
    except ImportError:  # pip install truststore; without it certifi's bundle is used
        pass
    return session


def download(url: str) -> tuple[bytes, str, str]:
    """Return response bytes, content type, and final URL after redirects."""
    parsed = urlsplit(url)
    urls = [url]
    if parsed.scheme.lower() == "http":
        urls = [urlunsplit(parsed._replace(scheme="https")), url]

    last_error = None
    for candidate in urls:
        try:
            response = _session().get(
                candidate,
                timeout=min(TOOL_TIMEOUT_S, 60),
                headers={"User-Agent": "Mozilla/5.0 (TrueCost index reader)"},
            )
            response.raise_for_status()
        except requests.RequestException as error:
            last_error = error
            continue
        return (
            response.content,
            response.headers.get("content-type", ""),
            response.url,
        )
    if last_error is not None:
        raise last_error
    raise requests.RequestException(f"Unable to download {url}")


def _rows_text(rows, name: str) -> str:
    lines = [f"[sheet {name}]"]
    for i, row in enumerate(rows, 1):
        cells = [str(c).strip() for c in row if str(c).strip() not in ("", "None")]
        if cells:
            lines.append(f"{i}: " + " | ".join(cells))
    return "\n".join(lines)


def to_text(raw: bytes, url: str, content_type: str) -> str:
    """Any published file as plain text the model can transcribe from."""
    kind = (urlparse(url).path.rsplit(".", 1)[-1] + " " + content_type).lower()
    if raw[:2] == b"PK" and ("xlsx" in kind or "spreadsheetml" in kind):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
        return "\n".join(
            _rows_text(ws.iter_rows(values_only=True), ws.title)
            for ws in wb.worksheets
        )
    if raw[:2] == b"PK":                                            # zip: first csv / xls(x) inside
        z = zipfile.ZipFile(io.BytesIO(raw))
        name = next(n for n in z.namelist() if n.lower().endswith((".csv", ".xls", ".xlsx")))
        return to_text(z.read(name), name, "")
    if raw[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" or "ms-excel" in kind:    # legacy .xls
        import xlrd
        book = xlrd.open_workbook(file_contents=raw)
        return "\n".join(
            _rows_text(
                (sheet.row_values(row) for row in range(sheet.nrows)),
                sheet.name,
            )
            for sheet in book.sheets()
        )
    if raw[:4] == b"%PDF":
        from pypdf import PdfReader
        return "\n".join(f"[page {i}]\n{p.extract_text() or ''}"
                         for i, p in enumerate(PdfReader(io.BytesIO(raw)).pages, 1))

    text = raw.decode("utf-8", errors="ignore")
    is_html = (
        "html" in kind
        or "<table" in text.lower()
        or re.search(r"<(?:!doctype\s+html|html\b)", text, re.IGNORECASE)
        is not None
    )
    if is_html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, "lxml")
        out = []
        for t in soup.find_all("table"):
            out += [" | ".join(c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"]))
                    for tr in t.find_all("tr")]
        return "\n".join(out) if out else ""
    return text


# -----------------------------------------------------------------------------
# 3. model transcribes the series (copies printed values only)
# -----------------------------------------------------------------------------
_TRANSCRIBE = """\
Below is the text of an OFFICIAL statistics file. Find the ONE series described here:
  {meaning}
Return ONLY JSON: {{"series_label": "<the row / column label as printed>", "frequency": "annual|monthly|quarterly", "values": [{{"period": "YYYY" or "YYYY-MM", "value": <number as printed>}}, ...], "note": ""}}
Rules: copy the printed numbers exactly - never compute, average, interpolate or convert. Use the headline / all-items / national row unless the description names a sub-index or region. If the file does not contain this series, return "values": [] and say why in note.

FILE ({url}):
{text}
"""

@cache
def _client():
    """One client for the process (a client created inline is garbage-collected mid-call)."""
    from google import genai
    return genai.Client(http_options=http_options(TOOL_TIMEOUT_S))


def focus(text: str, meaning: str) -> str:
    """A long file is cut to its header lines plus the rows that match the series
    description best."""
    if len(text) <= MAX_TEXT_CHARS:
        return text
    lines = text.splitlines()
    words = {w for w in re.findall(r"[a-z][a-z\-]{2,}", meaning.lower())} - {
        "index", "price", "the", "and", "for", "base", "monthly", "annual", "series",
        "india", "calendar", "year", "row", "sub"}
    score = lambda ln: sum(w in ln.lower() for w in words)
    best = max((score(ln) for ln in lines[5:]), default=0)
    keep = lines[:5] + [ln for ln in lines[5:] if best and score(ln) >= max(1, best - 1)]
    return "\n".join(keep)[:MAX_TEXT_CHARS]


def transcribe(text: str, url: str, meaning: str) -> dict:
    from google.genai import types

    resp = _client().models.generate_content(
        model=model_for("transcribe"),
        contents=_TRANSCRIBE.format(meaning=meaning, url=url, text=focus(text, meaning)),
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    return json.loads(resp.text)


MIN_MONTHS = 10                  # a year with fewer published months is not averaged


def to_annual(values: list[dict]) -> tuple[dict[int, float], dict[int, int]]:
    """Monthly -> calendar-year mean of the published months; annual stays as is.
    Returns (annual, months_per_year) so partial years stay visible in the provenance."""
    by_year: dict[int, list[float]] = {}
    for v in values:
        m = re.match(r"(\d{4})", str(v.get("period", "")))
        if m and isinstance(v.get("value"), (int, float)):
            by_year.setdefault(int(m.group(1)), []).append(float(v["value"]))
    monthly = any(re.match(r"\d{4}-\d{2}", str(v.get("period", ""))) for v in values)
    need = MIN_MONTHS if monthly else 1
    kept = {y: xs for y, xs in sorted(by_year.items()) if len(xs) >= need}
    return ({y: round(sum(xs) / len(xs), 4) for y, xs in kept.items()},
            {y: len(xs) for y, xs in kept.items()} if monthly else {})


# -----------------------------------------------------------------------------
# 4. validate + freeze
# -----------------------------------------------------------------------------
def validate(annual: dict[int, float]) -> list[str]:
    problems = []
    if len(annual) < MIN_YEARS:
        problems.append(f"only {len(annual)} complete year(s); need at least {MIN_YEARS}")
    if any(v <= 0 for v in annual.values()):
        problems.append("non-positive values")
    years = sorted(annual)
    for a, b in zip(years, years[1:]):
        if abs(annual[b] / annual[a] - 1) > MAX_YOY_JUMP:
            problems.append(f"{a}->{b} changes by more than {MAX_YOY_JUMP:.0%}: misread or wrong series")
    return problems


def read_official_series(url: str, meaning: str) -> dict:
    """Read, validate, and trace one series from an official source URL."""
    ok, why = official_domain(url)
    if not ok:
        return {"status": "fail", "note": f"refused: {why}"}
    try:
        raw, ctype, final_url = download(url)
    except requests.RequestException as e:
        return {"status": "fail", "note": f"download failed: {e}"}
    final_is_official, final_why = official_domain(final_url)
    if not final_is_official:
        return {"status": "fail", "note": f"refused after redirect: {final_why}"}
    why = final_why

    is_html = (
        "html" in ctype.lower()
        or b"<table" in raw[:4096].lower()
        or re.search(rb"<(?:!doctype\s+html|html\b)", raw[:4096], re.IGNORECASE)
        is not None
    )
    links = (
        rank_links(data_links(raw, final_url), meaning)
        if is_html
        else []
    )
    text = to_text(raw, final_url, ctype)
    if not text.strip():
        return {
            "status": "fail",
            "note": "no readable data on this page",
            "data_links": links[:4],
        }

    got = transcribe(text, final_url, meaning)
    values = got.get("values") or []
    unsupported_values = not_in_file(values, text)
    if unsupported_values:
        count = len(unsupported_values)
        return {
            "status": "fail",
            "note": (
                f"{count} transcribed value(s) are not printed in this file; "
                "the series is not on this page"
            ),
            "data_links": links[:4],
        }

    annual, months = to_annual(values)
    if problems := validate(annual):
        return {
            "status": "fail",
            "note": "; ".join(problems)
            + (f" ({got.get('note')})" if got.get("note") else ""),
            "data_links": links[:4],
        }
    return {"status": "ok", "annual": annual, "label": got.get("series_label", ""),
            "provenance": {"url": final_url, "official": why, "frequency": got.get(
                "frequency", ""),
                           "partial_years": {str(y): n for y, n in months.items()
                               if n < 12},
                           "downloaded_at": datetime.now(timezone.utc).isoformat(
                               timespec="seconds"),
                           "sha256": hashlib.sha256(raw).hexdigest()}}


def freeze(folder: Path, key: str, symbol: str, result: dict) -> Path:
    """Write the series + provenance to <folder>/<key>.json (one file per series,
    shared by bidders)."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{key}.json"
    path.write_text(json.dumps({"series_key": key, "symbol": symbol, "label":
        result["label"],
                                "annual_values": {str(y): v for y, v in result
                                ["annual"].items()},
                                **result["provenance"]}, indent=1,
                                ensure_ascii=False))
    return path
