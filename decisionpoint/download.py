#!/usr/bin/env python3
"""Download DecisionPoint charts without touching the main report pipeline."""

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import subprocess
import time

BASE = "https://stockcharts.com"
PAGE = BASE + "/freecharts/dpgallery.html"
TITLES = [
    "Daily Trend Analysis", "Weekly Trend Analysis", "Monthly Trend Analysis",
    "Short-Term Oscillator", "Intermediate-Term Oscillator", "Market Strength",
    "Price Momentum Oscillator", "Advance-Decline Lines", "Net New 52-Week Highs",
    "McClellan Oscillator", "Investor Sentiment", "Rydex Total Asset Ratio",
]


def fetch(url):
    # curl is used so this experiment needs no additional Python packages.
    return subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error",
         "--retry", "2", "--max-time", "60", "--user-agent", "Mozilla/5.0",
         "--referer", PAGE, url],
        check=True, stdout=subprocess.PIPE,
    ).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", choices=["SPX", "INDU", "NDX", "OEX", "all"],
                        default="SPX")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "downloads")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    # The page populates chart sources from this JSON, rather than just its HTML.
    config = json.loads(fetch(BASE + "/freecharts/dpgallery.json?r=" + str(time.time_ns())))
    records = []
    failures = []
    for gallery in config["galleries"]:
        symbol = gallery["index"]
        if args.gallery not in ("all", symbol):
            continue
        for number, query in enumerate(gallery["urls"], 1):
            title = TITLES[number - 1] if number <= len(TITLES) else f"Chart {number}"
            slug = title.lower().replace(" ", "-")
            filename = f"{symbol.lower()}-{number:02d}-{slug}.png"
            url = BASE + "/c-sc/sc?" + query + "&a=353809661"
            try:
                data = fetch(url)
                if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Response is not a PNG image")
                (args.output / filename).write_bytes(data)
                records.append({"gallery": symbol, "title": title, "file": filename,
                                "url": url, "bytes": len(data)})
                print(f"Saved {filename} ({len(data):,} bytes)", flush=True)
            except (subprocess.CalledProcessError, ValueError) as exc:
                failures.append({"url": url, "error": str(exc)})
                print(f"Failed {filename}: {exc}", flush=True)
            time.sleep(0.5)

    manifest = {"source": PAGE, "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "images": records, "failures": failures}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    figures = "\n".join(
        f'<figure><figcaption>{html.escape(r["gallery"] + " — " + r["title"])}</figcaption>'
        f'<a href="{html.escape(r["url"], quote=True)}">'
        f'<img loading="lazy" src="{r["file"]}" alt="{html.escape(r["title"], quote=True)}">'
        '</a></figure>' for r in records
    )
    (args.output / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>DecisionPoint chart snapshot</title>'
        '<style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:1rem}'
        'figure{margin:2rem 0}img{max-width:100%;height:auto}figcaption{font-weight:bold}</style>'
        '<h1>DecisionPoint chart snapshot</h1>'
        f'<p>Source: <a href="{PAGE}">StockCharts</a>. '
        f'Downloaded {html.escape(manifest["downloaded_at"])}.</p>' + figures + '</html>\n'
    )
    print(f"\nDownloaded {len(records)} images; {len(failures)} failures. "
          f"Open {args.output / 'index.html'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
