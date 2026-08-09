#!/usr/bin/env bash
# Installer for the Theorist Toolbox Claude Code skills.
#
#   ./install.sh                 install the skills to ~/.claude/skills/
#   ./install.sh --with-agents   also install the co-math agents to ~/.claude/agents/
#   ./install.sh --with-co-math  also install co-math/ (strict-mode hooks + tools) to ~/.claude/co-math/
#   ./install.sh --all           all of the above
#   ./install.sh --dry-run       show what would happen without writing anything
#   ./install.sh --dest DIR      install under DIR instead of ~/.claude
#
# Anything that would be overwritten is first moved to
# <dest>/backups/theorist-toolbox-<timestamp>/.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude"
DRY_RUN=0
WITH_AGENTS=0
WITH_CO_MATH=0

usage() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --with-agents)  WITH_AGENTS=1 ;;
    --with-co-math) WITH_CO_MATH=1 ;;
    --all)          WITH_AGENTS=1; WITH_CO_MATH=1 ;;
    --dry-run)      DRY_RUN=1 ;;
    --dest)
      [ $# -ge 2 ] || { echo "error: --dest requires a directory argument" >&2; exit 1; }
      DEST="$2"; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              echo "error: unknown option: $1" >&2; echo >&2; usage >&2; exit 1 ;;
  esac
  shift
done

[ -d "$REPO_DIR/skills" ] || { echo "error: $REPO_DIR/skills not found — run this from a checkout of theorist-toolbox" >&2; exit 1; }

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$DEST/backups/theorist-toolbox-$STAMP"
BACKED_UP=0
INSTALLED=0

say()  { echo "  $*"; }
note() { echo "$*"; }

# back up <path> (relative to $DEST) if it exists, then remove it
backup() {
  local rel="$1" target="$DEST/$1"
  [ -e "$target" ] || return 0
  if [ "$DRY_RUN" = 1 ]; then
    say "would back up $target -> $BACKUP_DIR/$rel"
  else
    mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
    mv "$target" "$BACKUP_DIR/$rel"
  fi
  BACKED_UP=$((BACKED_UP + 1))
}

# copy $REPO_DIR/<src> to $DEST/<rel>, backing up any existing target
install_one() {
  local src="$1" rel="$2"
  backup "$rel"
  if [ "$DRY_RUN" = 1 ]; then
    say "would install $rel"
  else
    mkdir -p "$DEST/$(dirname "$rel")"
    cp -R "$REPO_DIR/$src" "$DEST/$rel"
    say "installed $rel"
  fi
  INSTALLED=$((INSTALLED + 1))
}

note "Installing Theorist Toolbox to $DEST$([ "$DRY_RUN" = 1 ] && echo ' (dry run)' || true)"

note "Skills:"
for dir in "$REPO_DIR"/skills/*/; do
  name="$(basename "$dir")"
  install_one "skills/$name" "skills/$name"
done

if [ "$WITH_AGENTS" = 1 ]; then
  note "Agents (co-math team roles):"
  for f in "$REPO_DIR"/agents/*.md; do
    install_one "agents/$(basename "$f")" "agents/$(basename "$f")"
  done
fi

if [ "$WITH_CO_MATH" = 1 ]; then
  note "co-math strict-mode hooks + tools:"
  install_one "co-math" "co-math"
fi

# --- verification -----------------------------------------------------------

if [ "$DRY_RUN" = 0 ]; then
  note "Verifying installed skills:"
  FAILED=0
  for dir in "$REPO_DIR"/skills/*/; do
    name="$(basename "$dir")"
    manifest="$DEST/skills/$name/SKILL.md"
    if [ ! -f "$manifest" ]; then
      say "FAIL $name: missing SKILL.md"; FAILED=1; continue
    fi
    if ! head -20 "$manifest" | grep -q '^name:' || ! head -20 "$manifest" | grep -q '^description:'; then
      say "FAIL $name: SKILL.md frontmatter lacks name:/description:"; FAILED=1; continue
    fi
    say "ok   $name"
  done
  [ "$FAILED" = 0 ] || { echo "error: verification failed — see above" >&2; exit 1; }
fi

# --- summary ----------------------------------------------------------------

echo
if [ "$BACKED_UP" -gt 0 ] && [ "$DRY_RUN" = 0 ]; then
  note "Backed up $BACKED_UP existing item(s) to $BACKUP_DIR"
fi
if [ "$DRY_RUN" = 1 ]; then
  note "Dry run: $INSTALLED item(s) would be installed. Re-run without --dry-run to apply."
else
  note "Done: $INSTALLED item(s) installed."
fi

if [ "$WITH_CO_MATH" = 0 ]; then
  note "Note: the co-math workflow (co-math-init / co-math-status) needs the agents and"
  note "the hooks in co-math/ — re-run with --all if you plan to use it."
fi
if [ "$DRY_RUN" = 0 ]; then
  note "Invoke the skills from Claude Code: /math-proof, /co-math-init, ..."
fi
