# shellcheck shell=bash
# Shared prompt preflight and copying. Each bootstrap supplies its safe copy_file.
validate_shared_prompts() {
  local shared_dir="$1" specific_dir="$2"
  local source name body
  local description_pattern='^description: [A-Za-z]([A-Za-z0-9 ,./()_-]*[A-Za-z0-9,./()_-])?$'
  local -a lines

  for source in "$shared_dir"/*; do
    [[ -e "$source" || -L "$source" ]] || continue
    name="${source##*/}"
    if [[ ! -f "$source" || -L "$source" || ! "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*\.md$ ]]; then
      echo "Shared prompts must be flat, regular <lowercase-name>.md files: $source" >&2
      return 1
    fi
    mapfile -t lines <"$source"
    # One plain description avoids YAML coercion and harness-only metadata.
    if [[ "${lines[0]:-}" != '---' || "${lines[2]:-}" != '---' ||
          ! "${lines[1]:-}" =~ $description_pattern ]]; then
      echo "Shared prompt requires only a single plain description field: $source" >&2
      return 1
    fi
    case "${lines[1],,}" in
      'description: true'|'description: false'|'description: null'|'description: yes'|'description: no'|'description: on'|'description: off')
        echo "Shared prompt description must be text, not a YAML scalar: $source" >&2
        return 1
        ;;
    esac
    body="${lines[*]:3}"
    body="${body//\$ARGUMENTS/}"
    if [[ "$body" =~ \$([0-9@a-zA-Z_]|\{) || "$body" == *'!`'* ||
          "$body" =~ (^|[[:space:]])@[a-zA-Z0-9_./-] ]]; then
      echo "Shared prompt contains nonportable argument, shell, or file-reference syntax: $source" >&2
      return 1
    fi
    if [[ -e "$specific_dir/$name" || -L "$specific_dir/$name" ]]; then
      echo "Shared/harness-specific prompt collision: $name in $specific_dir" >&2
      return 1
    fi
  done
}

copy_shared_prompts() {
  local shared_dir="$1" target_dir="$2" source

  for source in "$shared_dir"/*.md; do
    [[ -f "$source" ]] || continue
    copy_file "$source" "$target_dir/${source##*/}"
  done
}
