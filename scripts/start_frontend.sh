#!/bin/bash
# Running frontend script
FRONTEND_DIR="$(dirname "$0")/../frontend"
cd "${FRONTEND_DIR}"
npm test
npm run dev
