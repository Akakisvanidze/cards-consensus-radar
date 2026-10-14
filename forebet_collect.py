import json
import re
from pathlib import Path
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URL = "https://www.forebet.com/en/football-tips-and-predictions-for-today/"
OUT = Path("data/forebet/latest.json")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
matches = []

for row in soup.select(".rcnt"):
    probability_box = row.select_one(".fprc")
    if not probability_box:
        continue

    spans = probability_box.find_all("span", recursive=False)
    if len(spans) < 3:
        continue

    try:
        values = [float(spans[i].get_text(strip=True).replace("%", "")) for i in range(3)]
    except ValueError:
        continue

    if not 98 <= sum(values) <= 102:
        continue

    home_tag = row.select_one('[itemprop="homeTeam"] [itemprop="name"]')
    away_tag = row.select_one('[itemprop="awayTeam"] [itemprop="name"]')

    if not home_tag or not away_tag:
        continue

    probabilities = dict(zip(("1", "X", "2"), values))
    qualified = [
        {"market": market, "probability": value}
        for market, value in probabilities.items()
        if value >= 70
    ]

    matches.append({
        "home": home_tag.get_text(strip=True),
        "away": away_tag.get_text(strip=True),
        "probabilities": probabilities,
        "qualified": qualified
    })

if not matches:
    raise RuntimeError("Forebet-ის მონაცემები ვერ წავიკითხეთ. ძველი ფაილი უცვლელი დარჩა.")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps({
        "source": "Forebet",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "matches": matches
    }, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"Read {len(matches)} matches.")
print(f"70% selections: {sum(len(m['qualified']) for m in matches)}")
