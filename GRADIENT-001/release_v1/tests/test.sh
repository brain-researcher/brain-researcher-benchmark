#!/bin/bash
set -euo pipefail
cd /tests
python3 -I -B -c 'import sys, runpy; sys.path.insert(0, "/tests"); runpy.run_path("/tests/verify.py", run_name="__main__")'
