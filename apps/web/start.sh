#!/bin/sh
# Next.js standalone mode doesn't copy public/ or .next/static/ automatically.
# Copy them into the standalone output so the server can serve them.
cp -r public .next/standalone/public 2>/dev/null || true
cp -r .next/static .next/standalone/.next/static 2>/dev/null || true
exec node .next/standalone/server.js
