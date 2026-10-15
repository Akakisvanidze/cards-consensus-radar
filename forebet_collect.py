import json
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://kiqiq.com/api/v1/predictions"
OUTPUT = Path("data/forebet/latest.json")

response = requests.get(
    URL,
    params={"limit": 100},
    timeout=30
)
response.raise_for_status()

data = response.json()
fixtures = data.get("fixtures")

if not isinstance(fixtures, list):
    raise RuntimeError("API did not return a fixtures list")

matches = []

for game in fixtures:
    try:
        probabilities = {
            "1": round(float(game["home_win_prob"]) * 100, 1),
            "X": round(float(game["draw_prob"]) * 100, 1),
            "2": round(float(game["away_win_prob"]) * 100, 1)
        }

        if not 98 <= sum(probabilities.values()) <= 102:
            continue

        qualified = [
            {"market": market, "probability": probability}
            for market, probability in probabilities.items()
            if probability >= 70
        ]

        matches.append({
            "fixture_id": game.get("fixture_id"),
            "home": game["home"],
            "away": game["away"],
            "league": game.get("competition"),
            "kickoff": game.get("kickoff_iso"),
            "probabilities": probabilities,
            "qualified": qualified
        })

    except (KeyError, ValueError, TypeError):
        continue

if not matches:
    print("No valid matches returned. Existing data preserved.")
else:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps({
            "source": "KiqIQ",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "matches": matches
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Saved {len(matches)} matches")
    print(f"70% picks: {sum(len(m['qualified']) for m in matches)}")
