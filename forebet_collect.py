#!/usr/bin/env python3
"""Conservative Forebet probability extraction: reject ambiguous or missing values."""
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL = 'https://www.forebet.com/en/football-tips-and-predictions-for-today/'
OUT = Path('data/forebet/latest.json')

def parse(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for row in soup.select('.rcnt'):
        ps = row.select('.fprc span')
        home, away = row.select_one('.homeTeam'), row.select_one('.awayTeam')
        if len(ps) != 3 or home is None or away is None:
            continue
        strings = [p.get_text(' ', strip=True) for p in ps]
        if not all(re.fullmatch(r'\d{1,3}%?', s) for s in strings):
            continue
        nums = [int(s.rstrip('%')) for s in strings]
        if any(n > 100 for n in nums) or not 98 <= sum(nums) <= 102:
            continue
        h, a = home.get_text(' ', strip=True), away.get_text(' ', strip=True)
        if not h or not a:
            continue
        results.append({'home': h, 'away': a, 'probabilities': dict(zip(('1','X','2'), nums)), 'qualified': [{'market': k, 'probability': v} for k,v in zip(('1','X','2'),nums) if v >= 70]})
    return results

def main():
    response = requests.get(URL, timeout=30, headers={'User-Agent':'Mozilla/5.0'})
    response.raise_for_status()
    matches = parse(response.text)
    if not matches:
        raise RuntimeError('No validated probabilities; existing output preserved')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps({'source':'Forebet','source_url':URL,'updated_at':datetime.now(timezone.utc).isoformat(),'matches':matches}, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(OUT)
    print(f'Validated {len(matches)} matches')

if __name__ == '__main__':
    main()
