"""Download the latest 10-K per ticker from SEC EDGAR (SEC-compliant headers + rate limiting)."""
import logging
import time

import requests
from sqlalchemy import text

from finsight.config import FILINGS_DIR, SEC_USER_AGENT
from finsight.db.engine import get_engine

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
# ExxonMobil's ticker maps to a successor registrant (8-K12B only, no 10-K history).
# The legacy CIK holds the 10-K filings.
CIK_OVERRIDES = {"XOM": "0000034088"}
_last_call = 0.0


def _get(url: str) -> requests.Response:
    global _last_call
    wait = 0.15 - (time.time() - _last_call)  # SEC limit is 10 req/s; stay well below
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers=HEADERS, timeout=60)
    _last_call = time.time()
    r.raise_for_status()
    return r


def ticker_to_cik() -> dict[str, str]:
    data = _get("https://www.sec.gov/files/company_tickers.json").json()
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}


def _find_10k(block: dict):
    forms = block.get("form", [])
    for i, form in enumerate(forms):
        if form == "10-K":
            return block["accessionNumber"][i], block["primaryDocument"][i], block["filingDate"][i]
    return None


def latest_10k(cik: str):
    sub = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    hit = _find_10k(sub["filings"]["recent"])
    if hit:
        return hit
    for f in sub["filings"].get("files", []):  # pagination fallback for older filings
        hit = _find_10k(_get(f"https://data.sec.gov/submissions/{f['name']}").json())
        if hit:
            return hit
    return None


def download_filings(tickers: list[str] | None = None) -> int:
    eng = get_engine()
    with eng.connect() as c:
        tks = tickers or [r[0] for r in c.execute(text("SELECT ticker FROM companies ORDER BY ticker"))]
    mapping = ticker_to_cik()
    done = 0
    for tk in tks:
        out = FILINGS_DIR / f"{tk}_10K.html"
        if out.exists() and out.stat().st_size > 10_000:
            done += 1
            continue
        try:
            cik = CIK_OVERRIDES.get(tk) or mapping.get(tk.upper().replace("-", "."))
            if not cik:
                log.warning("%s: no CIK found", tk)
                continue
            hit = latest_10k(cik)
            if not hit:
                log.warning("%s: no 10-K found for CIK %s", tk, cik)
                continue
            acc, doc, _date = hit
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"
            out.write_bytes(_get(url).content)
            with eng.begin() as c:
                c.execute(text("UPDATE companies SET cik=:k WHERE ticker=:t"), {"k": cik, "t": tk})
            log.info("%s: saved %s", tk, out.name)
            done += 1
        except Exception as e:
            log.error("%s failed: %s", tk, e)
    return done
