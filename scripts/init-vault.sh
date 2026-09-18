#!/usr/bin/env bash
# Scaffold a minimal Obsidian vault for think-smarterer / smart-notes.
# Idempotent: creates missing dirs/files; never overwrites existing files.
set -euo pipefail

usage() {
  echo "Usage: $0 <vault-path>" >&2
  echo "  Creates 00-Inbox/, Literature/, Permanent/, Hypotheses/, Projects/, _Archive/" >&2
  echo "  plus stub Permanent/00-home.md and Hypotheses/00-INDEX.md if absent." >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
VAULT="$1"
TODAY="$(date +%Y-%m-%d)"

mkdir -p \
  "$VAULT/00-Inbox" \
  "$VAULT/Literature" \
  "$VAULT/Permanent" \
  "$VAULT/Hypotheses" \
  "$VAULT/Projects" \
  "$VAULT/_Archive"

HOME_NOTE="$VAULT/Permanent/00-home.md"
if [[ ! -e "$HOME_NOTE" ]]; then
  cat >"$HOME_NOTE" <<EOF
---
title: Home
status: living
type: structure
tags: [home]
created: $TODAY
---

# Vault home

Entry map for this vault. Link project indexes and standing hubs here as they appear.
EOF
fi

HYP_INDEX="$VAULT/Hypotheses/00-INDEX.md"
if [[ ! -e "$HYP_INDEX" ]]; then
  cat >"$HYP_INDEX" <<EOF
---
title: Hypotheses index
status: living
type: project-index
tags: [hypotheses]
created: $TODAY
---

# Hypotheses

## Open

## Graduated

## Resolved
EOF
fi

# Marker so vault-doctor can auto-detect this as a vault root
mkdir -p "$VAULT/.obsidian"
if [[ ! -e "$VAULT/.obsidian/app.json" ]]; then
  echo '{}' >"$VAULT/.obsidian/app.json"
fi

echo "Vault ready: $VAULT"
echo "Set SMART_NOTES_VAULT=$VAULT"
