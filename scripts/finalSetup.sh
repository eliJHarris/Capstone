#!/usr/bin/env bash
set -euo pipefail

sudo docker compose up --build -d

./generatingDBpass.sh

./buildLDAP.sh


echo ""
sudo docker compose ps
echo ""
echo "Tailing logs (Ctrl+C to stop)…"
sudo docker compose logs -f
