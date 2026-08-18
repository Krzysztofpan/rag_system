#!/usr/bin/env bash
set -euo pipefail

pids=()

kill_tree() {
    local pid="$1"
    local sig="$2"
    local child
    for child in $(pgrep -P "$pid" 2>/dev/null || true); do
        kill_tree "$child" "$sig"
    done
    kill -s "$sig" "$pid" 2>/dev/null || true
}

cleanup() {
    trap - EXIT INT TERM
    local pid
    for pid in "${pids[@]}"; do
        kill_tree "$pid" TERM
    done
    sleep 0.4
    for pid in "${pids[@]}"; do
        kill_tree "$pid" KILL
    done
    wait 2>/dev/null || true
}

trap cleanup EXIT INT TERM

(cd backend && exec uv run main.py) &
pids+=("$!")
(cd frontend && exec npm run dev) &
pids+=("$!")

wait -n || true
