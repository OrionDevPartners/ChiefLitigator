#!/usr/bin/env bash
set -euo pipefail

echo "=== Building cyphergy.ai frontend ==="
cd frontend
NODE_ENV=production npm run build
find out/ .next/ -name "*.map" -delete 2>/dev/null || true
echo "Source maps purged."

echo "=== Building admin.cyphergy.ai ==="
cd ../admin-frontend
NODE_ENV=production npm run build
find out/ .next/ -name "*.map" -delete 2>/dev/null || true
echo "Admin source maps purged."

echo "=== Production builds complete ==="
