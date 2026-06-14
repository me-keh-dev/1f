# -*- coding: utf-8 -*-
"""OurAirports の airports.csv を取得（パブリックドメイン）。deploy/ローカルで実行。
  python fetch_airports.py [out_path]
"""
import sys
import requests

URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "airports.csv"
    r = requests.get(URL, headers={"User-Agent": "flight-tracker/0.1"}, timeout=60)
    r.raise_for_status()
    with open(out, "wb") as f:
        f.write(r.content)
    print(f"saved {out} ({len(r.content)//1024} KB) - OurAirports (Public Domain)")


if __name__ == "__main__":
    main()
