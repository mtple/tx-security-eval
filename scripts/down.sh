#!/usr/bin/env bash
cd "$(dirname "$0")/.."
[ -f .anvil.pid ] && kill "$(cat .anvil.pid)" 2>/dev/null && rm -f .anvil.pid && echo "anvil stopped" || echo "anvil not running"
