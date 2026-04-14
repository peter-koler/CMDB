#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "Usage: $0 <host> <port> <username> [ssh_options]"
  echo "Example: $0 192.168.31.182 2223 think"
  echo "Example: $0 192.168.31.182 2223 think \"-o StrictHostKeyChecking=no\""
  exit 1
fi

HOST="$1"
PORT="$2"
USER="$3"
EXTRA_OPTS="${4:-}"

echo "[1/2] Basic SSH echo test..."
if [[ -n "$EXTRA_OPTS" ]]; then
  # shellcheck disable=SC2086
  ssh $EXTRA_OPTS -p "$PORT" "$USER@$HOST" 'echo __ARCO_TEST__'
else
  ssh -p "$PORT" "$USER@$HOST" 'echo __ARCO_TEST__'
fi

echo
echo "[2/2] Bundle section test (sh -s via stdin)..."
if [[ -n "$EXTRA_OPTS" ]]; then
  # shellcheck disable=SC2086
  ssh $EXTRA_OPTS -p "$PORT" "$USER@$HOST" 'sh -s' <<'EOF'
echo "__ARCO_SECTION_BEGIN__basic"
echo ok
echo "__ARCO_SECTION_END__basic"
EOF
else
  ssh -p "$PORT" "$USER@$HOST" 'sh -s' <<'EOF'
echo "__ARCO_SECTION_BEGIN__basic"
echo ok
echo "__ARCO_SECTION_END__basic"
EOF
fi

echo
echo "Done."
