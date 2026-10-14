import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

KEY = os.environ["API_FOOTBALL_KEY"]
BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": KEY}
OUT = Path("data/forebet/latest.json")
MAX_PREDICTIONS = 10


def api(endpoint, params):
    response = requests.get(
        BASE + "/" + endpoint,
        headers=HEADERS,
        params=params,
        timeout=30
    )
    if response.status_code == 429:
        print("API request limit reached; stopping.")
        return None
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        print("API error:", data["errors"])
        return None
    return data.get("response", [])


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    fixtures = api("fixtures", {"date": today})
    if fixtures is None:
        return

    matches = []
    checked = 0

    for item in fixtures:
        if checked >= MAX_PREDICTIONS:
            break

        fixture = item.get("fixture", {})
        if fixture.get("status", {}).get("short") != "NS":
            continue

        fixture_id = fixture.get("id")
        if not fixture_id:
            continue

        predictions = api("predictions", {"fixture": fixture_id})
        if predictions is None:
            break

        checked += 1
        if not predictions:
            continue

        prediction = predictions[0].get("predictions", {})
        percent = prediction.get("percent", {})
        probabilities = {}

        for market, field in [
            ("1", "home"),
            ("X", "draw"),
            ("2", "away")
        ]:
            value = percent.get(field)
            if isinstance(value, str) and value.endswith("%"):
                try:
                    probabilities[market] = float(value[:-1])
                except ValueError:
                    pass

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
        print("No validated predictions; previous data preserved.")
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

    print(f"Checked {checked} matches; saved {len(matches)}.")


if __name__ == "__main__":
    main()
