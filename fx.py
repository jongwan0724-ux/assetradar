"""원/달러 환율(ECB 기준, Frankfurter API, 키 불필요)."""
from __future__ import annotations

import json
import urllib.request

URL = "https://api.frankfurter.dev/v1/latest?from=USD&to=KRW"


def parse(payload: dict) -> dict:
    return {"rate": float(payload["rates"]["KRW"]), "date": payload["date"], "source": "Frankfurter (ECB)"}


def fetch(prev: dict | None) -> dict:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "AssetRadarBot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return parse(json.load(r))
    except Exception as e:
        print(f"[fx] 환율을 못 받아서 이전 값을 씁니다: {e}")
        return prev or {"rate": 1345.9, "date": "2026-11-23", "source": "seed"}
