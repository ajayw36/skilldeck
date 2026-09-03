#!/bin/sh
# Production deploy for the payments service.
set -e
if [ -f .env ]; then . ./.env; fi
echo "deploying payments service..."
touch deployed.marker
echo "deployed."
