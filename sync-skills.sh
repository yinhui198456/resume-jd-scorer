#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-/opt/personal-agent-workspace}"
WORKSPACE_SKILLS="${WORKSPACE}/skills"
CLAUDE_SKILLS="${CLAUDE_SKILLS:-${HOME}/.claude/skills}"

usage() {
  cat <<'USAGE'
Usage:
  ./sync-skills.sh --check
  ./sync-skills.sh [skill-name]
  ./sync-skills.sh --all

Rules:
  - /opt/personal-agent-workspace/skills/<skill-name>/ is the source of truth.
  - Claude Code skill directories should be symlinks to the workspace source.
  - If a Claude Code entry is a real directory, this script copies from workspace to Claude Code.
  - This script never copies from Claude Code back into the workspace.
USAGE
}

skill_name_from_frontmatter() {
  local skill_file="$1"
  awk '
    NR == 1 && $0 == "---" { in_fm=1; next }
    in_fm && $0 == "---" { exit }
    in_fm && /^name:/ {
      sub(/^name:[[:space:]]*/, "", $0)
      gsub(/^"|"$/, "", $0)
      print $0
      exit
    }
  ' "$skill_file"
}

is_symlink_to() {
  local link_path="$1"
  local expected="$2"
  [[ -L "$link_path" ]] && [[ "$(readlink -f "$link_path")" == "$(readlink -f "$expected")" ]]
}

check_skill() {
  local skill_dir="$1"
  local skill
  skill="$(basename "$skill_dir")"

  if [[ -L "$skill_dir" ]]; then
    return 0
  fi

  local skill_file="${skill_dir}/SKILL.md"
  if [[ ! -f "$skill_file" ]]; then
    echo "FAIL: missing SKILL.md: ${skill_dir}"
    return 1
  fi

  local declared
  declared="$(skill_name_from_frontmatter "$skill_file")"
  if [[ -z "$declared" ]]; then
    echo "FAIL: missing frontmatter name: ${skill_file}"
    return 1
  fi

  if [[ "$declared" != "$skill" ]]; then
    echo "FAIL: directory/frontmatter mismatch: ${skill_dir} declares '${declared}'"
    return 1
  fi

  local claude_entry="${CLAUDE_SKILLS}/${skill}"
  if [[ -e "$claude_entry" || -L "$claude_entry" ]]; then
    if is_symlink_to "$claude_entry" "$skill_dir"; then
      echo "OK: ${skill} -> Claude symlink"
    elif [[ -d "$claude_entry" && -f "${claude_entry}/SKILL.md" ]]; then
      if diff -qr "$skill_dir" "$claude_entry" >/dev/null; then
        echo "OK: ${skill} -> Claude copy matches"
      else
        echo "FAIL: Claude copy differs: ${claude_entry}"
        return 1
      fi
    else
      echo "FAIL: invalid Claude entry: ${claude_entry}"
      return 1
    fi
  else
    echo "WARN: missing Claude entry: ${claude_entry}"
  fi
}

check_all() {
  local failed=0
  while IFS= read -r -d '' skill_dir; do
    check_skill "$skill_dir" || failed=1
  done < <(find "$WORKSPACE_SKILLS" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

  while IFS= read -r -d '' alias_path; do
    if [[ -L "$alias_path" ]]; then
      echo "OK: alias $(basename "$alias_path") -> $(readlink "$alias_path")"
    fi
  done < <(find "$WORKSPACE_SKILLS" -mindepth 1 -maxdepth 1 -type l -print0 | sort -z)

  return "$failed"
}

sync_one() {
  local skill="$1"
  local src="${WORKSPACE_SKILLS}/${skill}"
  local dest="${CLAUDE_SKILLS}/${skill}"

  if [[ ! -d "$src" ]]; then
    echo "ERROR: workspace skill not found: ${src}" >&2
    exit 2
  fi

  mkdir -p "$CLAUDE_SKILLS"

  if is_symlink_to "$dest" "$src"; then
    echo "OK: ${skill} already symlinked"
    return 0
  fi

  if [[ -L "$dest" ]]; then
    rm "$dest"
    ln -s "$src" "$dest"
    echo "OK: relinked ${dest} -> ${src}"
    return 0
  fi

  if [[ -e "$dest" ]]; then
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "${src}/" "${dest}/"
    else
      rm -rf "$dest"
      cp -a "$src" "$dest"
    fi
    echo "OK: copied ${skill} to Claude Code"
  else
    ln -s "$src" "$dest"
    echo "OK: linked ${dest} -> ${src}"
  fi
}

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 0
  fi

  case "$1" in
    --help|-h)
      usage
      ;;
    --check)
      check_all
      ;;
    --all)
      while IFS= read -r -d '' skill_dir; do
        sync_one "$(basename "$skill_dir")"
      done < <(find "$WORKSPACE_SKILLS" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
      ;;
    *)
      sync_one "$1"
      ;;
  esac
}

main "$@"
