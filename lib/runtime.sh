# shellcheck shell=bash
# Validate before writing. Managed directory links could redirect writes into sources.
validate_runtime_destination() {
  local runtime="$1" repo="$2" resolved root profile
  shift 2
  resolved="$(realpath -m -- "$runtime")"
  root="$(realpath -m -- "$repo")"
  profile="$(realpath -m -- "$HOME/profile")"
  case "$resolved" in
    /|"$(realpath -m -- "$HOME")"|"$root"|"$root"/*|"$profile"|"$profile"/*)
      echo "Refusing unsafe runtime destination: $runtime" >&2
      return 1
      ;;
  esac
  local directory
  for directory in "$@"; do
    if [[ -L "$runtime/$directory" ]]; then
      echo "Managed runtime directory must not be a symlink: $runtime/$directory" >&2
      return 1
    fi
  done
}
