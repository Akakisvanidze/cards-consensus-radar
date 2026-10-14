
import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

KEY = os.environ["API_FOOTBALL_KEY"]
BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": KEY}
OUT = Path("data/forebet/latest.json")


def api(endpoint, params):
    r = requests.get(
        BASE + "/" + endpoint,
        headers=HEADERS,
        params=params,
        timeout=30
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(str(data["errors"]))
    return data.get("response", [])


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    fixtures = api("fixtures", {"date": today})

    matches = []
    checked = 0

    for item in fixtures:
        if checked >= 70:
            break

        fixture = item.get("fixture", {})
        if fixture.get("status", {}).get("short") != "NS":
            continue

        fixture_id = fixture.get("id")
        if not fixture_id:
            continue

        checked += 1
        predictions = api("predictions", {"fixture": fixture_id})

        if not predictions:
            continue

        p = predictions[0].get("predictions", {})
        percent = p.get("percent", {})
        probabilities = {}

        for market, field in [
            ("1", "home"),
            ("X", "draw"),
            ("2", "away")
        ]:
            value = percent.get(field)
            if isinstance(value, str) and value.endswith("%"):
                probabilities[market] = int(value[:-1])

        if len(probabilities) != 3:
            continue

        qualified = [
            {"market": market, "probability": value}
            for market, value in probabilities.items()
            if value >= 70
        ]

        matches.append({
            "fixture_id": fixture_id,
            "home": item["teams"]["home"]["name"],
            "away": item["teams"]["away"]["name"],
            "probabilities": probabilities,
            "qualified": qualified
        })

    if not matches:
        print("No validated predictions; previous data preserved")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({
            "source": "API-Football",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "matches": matches
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Checked {checked} fixtures, saved {len(matches)}")


if __name__ == "__main__":
    main()
