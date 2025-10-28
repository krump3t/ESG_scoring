#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt

echo "Integration tests require LIVE_EMBEDDINGS=true and ALLOW_NETWORK=true along with WX_* and SEC_USER_AGENT secrets."
