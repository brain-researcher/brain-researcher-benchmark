#!/bin/bash
set -euo pipefail
mkdir -p /submission
cp /solution/oracle.pyz /submission/evaluate.py
python3 /submission/evaluate.py --data /data --output /submission/discovery.json --contract /public/contract.json
