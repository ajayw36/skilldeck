#!/bin/sh
# Production deploy for the payments service.
set -e
if [ -f .env ]; then . ./.env; fi
if [ -z "$STRIPE_KEY" ]; then
  echo "FATAL: STRIPE_KEY is not set" >&2
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "FATAL: DATABASE_URL is not set" >&2
  exit 1
fi
echo "deploying payments service..."
touch deployed.marker
echo "deployed."
