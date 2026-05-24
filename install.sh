#!/usr/bin/env bash
# Waddington installer — copies skills, agents, prompts, and SYSTEM.md
# into the Feynman agent directory (~/.feynman/agent/).
#
# Usage:
#   bash install.sh           # install into ~/.feynman/agent/
#   bash install.sh --dry-run # show what would be copied
#   bash install.sh --unlink  # remove previously installed files

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FEYNMAN_HOME="${FEYNMAN_HOME:-$HOME/.feynman}"
AGENT_DIR="$FEYNMAN_HOME/agent"
DRY_RUN=false
UNLINK=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --unlink)  UNLINK=true  ;;
  esac
done

log()  { echo "  $*"; }
ok()   { echo "✓ $*"; }
skip() { echo "~ $*"; }
err()  { echo "✗ $*" >&2; }

# ── sanity checks ────────────────────────────────────────────────────────────
if ! command -v feynman &>/dev/null && [[ "$DRY_RUN" == false ]]; then
  err "Feynman is not installed. Install it first:"
  err "  curl -fsSL https://feynman.is/install | bash"
  exit 1
fi

if [[ ! -d "$AGENT_DIR" && "$DRY_RUN" == false ]]; then
  err "Feynman agent directory not found: $AGENT_DIR"
  err "Run 'feynman' once to initialize it, then re-run this installer."
  exit 1
fi

echo ""
echo "Waddington installer"
echo "  Source : $REPO_ROOT"
echo "  Target : $AGENT_DIR"
echo "  Mode   : $( [[ $DRY_RUN == true ]] && echo 'dry-run' || ([[ $UNLINK == true ]] && echo 'unlink' || echo 'install') )"
echo ""

# ── manifest of what gets installed ─────────────────────────────────────────
declare -A MAPPINGS=(
  ["$REPO_ROOT/.waddington/agents"]="$AGENT_DIR/agents"
  ["$REPO_ROOT/skills"]="$AGENT_DIR/skills"
  ["$REPO_ROOT/prompts"]="$AGENT_DIR/prompts"
)
SYSTEM_SRC="$REPO_ROOT/.waddington/SYSTEM.md"
SYSTEM_DST="$AGENT_DIR/SYSTEM.md"

# ── unlink mode ──────────────────────────────────────────────────────────────
if [[ "$UNLINK" == true ]]; then
  MANIFEST="$FEYNMAN_HOME/.waddington-manifest"
  if [[ ! -f "$MANIFEST" ]]; then
    err "No manifest found at $MANIFEST — nothing to unlink."
    exit 1
  fi
  echo "Removing installed files..."
  while IFS= read -r dst; do
    if [[ -f "$dst" ]]; then
      rm "$dst"
      ok "removed $dst"
    fi
  done < "$MANIFEST"
  rm "$MANIFEST"
  echo ""
  echo "Waddington unlinked. Run 'feynman' to reload."
  exit 0
fi

# ── install mode ─────────────────────────────────────────────────────────────
MANIFEST_LINES=()

copy_tree() {
  local src="$1"
  local dst_root="$2"
  local label="$3"

  if [[ ! -d "$src" ]]; then
    skip "$label (source directory not found: $src)"
    return
  fi

  while IFS= read -r -d '' file; do
    rel="${file#$src/}"
    dst="$dst_root/$rel"

    if [[ "$DRY_RUN" == true ]]; then
      log "[dry] $label/$rel → $dst"
      continue
    fi

    mkdir -p "$(dirname "$dst")"

    if [[ -f "$dst" ]]; then
      # Back up user-modified files (keep ours as .waddington)
      src_hash="$(sha256sum "$file" | cut -d' ' -f1)"
      dst_hash="$(sha256sum "$dst"  | cut -d' ' -f1)"
      if [[ "$src_hash" != "$dst_hash" ]]; then
        cp "$dst" "${dst}.pre-waddington"
        skip "$label/$rel (backed up existing to .pre-waddington)"
      fi
    fi

    cp "$file" "$dst"
    MANIFEST_LINES+=("$dst")
    ok "$label/$rel"
  done < <(find "$src" -type f -print0)
}

# Copy agents, skills, prompts
for src in "${!MAPPINGS[@]}"; do
  dst="${MAPPINGS[$src]}"
  label="$(basename "$src")"
  copy_tree "$src" "$dst" "$label"
done

# Copy SYSTEM.md
if [[ "$DRY_RUN" == true ]]; then
  log "[dry] SYSTEM.md → $SYSTEM_DST"
else
  if [[ -f "$SYSTEM_DST" ]]; then
    cp "$SYSTEM_DST" "${SYSTEM_DST}.pre-waddington"
    skip "SYSTEM.md (backed up existing to .pre-waddington)"
  fi
  cp "$SYSTEM_SRC" "$SYSTEM_DST"
  MANIFEST_LINES+=("$SYSTEM_DST")
  ok "SYSTEM.md"
fi

# Write manifest
if [[ "$DRY_RUN" == false ]]; then
  printf '%s\n' "${MANIFEST_LINES[@]}" > "$FEYNMAN_HOME/.waddington-manifest"
fi

echo ""
if [[ "$DRY_RUN" == true ]]; then
  echo "Dry run complete — no files were copied."
else
  echo "Waddington installed successfully."
  echo "Run 'feynman' in your waddington/ directory to start."
  echo ""
  echo "To uninstall: bash install.sh --unlink"
fi
