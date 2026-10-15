import json
from pathlib import Path
from datetime import datetime, timezone

import requests

URL = "https://tipsaudit.com/api/v1/predictions"
OUTPUT = Path("data/forebet/latest.json")
THRESHOLD = 70

response = requests.get(
    URL,
    headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30
)
response.raise_for_status()

data = response.json()
predictions = data.get("predictions", [])

if not isinstance(predictions, list):
    raise RuntimeError("Invalid predictions data")

matches = []

for game in predictions:
    try:
        probs = game["fair_probabilities"]

        probabilities = {
            "1": round(float(probs["home"]) * 100, 1),
            "X": round(float(probs["draw"]) * 100, 1),
            "2": round(float(probs["away"]) * 100, 1)
        }

        if not 98 <= sum(probabilities.values()) <= 102:
            continue

        qualified = [
            {
                "market": market,
                "probability": probability
            }
            for market, probability in probabilities.items()
            if probability >= THRESHOLD
        ]

        matches.append({
            "fixture_id": game.get("id"),
            "home": game["home"],
            "away": game["away"],
            "league": game.get("league"),
            "kickoff": game.get("kickoff_utc"),
            "probabilities": probabilities,
            "qualified": qualified,
            "source_url": game.get("url")
        })

    except (KeyError, TypeError, ValueError):
        continue

if not matches:
    raise RuntimeError(
        "No valid matches. Existing data preserved."
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

OUTPUT.write_text(
    json.dumps({
        "source": "TipsAudit",
        "source_url": "https://tipsaudit.com",
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "matches": matches
    }, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

picks = sum(
    len(match["qualified"])
    for match in matches
)

print(f"Saved matches: {len(matches)}")
print(f"Predictions >= 70%: {picks}")
