#!/bin/bash
set -e

echo "==> Building API server..."
pnpm --filter @workspace/api-server run build

echo "==> Starting API server..."
node --enable-source-maps artifacts/api-server/dist/index.mjs &

echo "==> Starting bot..."
python bot/main.py
