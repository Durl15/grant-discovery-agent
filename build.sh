#!/usr/bin/env bash
# Netlify build script — runs the grant pipeline and produces a static site.
set -euo pipefail

echo "==> Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "==> Scanning grant sources..."
# Allow individual scrapers to fail (network blips) without killing the build
python run.py scan --limit 100 || {
  echo "WARN: scan exited with error — continuing with any cached data"
}

echo "==> Exporting grant data to public/..."
mkdir -p public/data
python run.py share --format json --output public/data/grants.json --n 200

count=$(python -c "import json; d=json.load(open('public/data/grants.json')); print(d['count'])")
echo "==> Exported ${count} grants."

echo "==> Build complete."
