"""Shared deployment preflight and the agents command. No harness binaries required."""

import argparse
import json
import os
import re
import runpy
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
skills = runpy.run_path(str(ROOT / "lib/skills"))
HARNESSES = ("pi", "opencode", "hermes", "claude")


def run(*args, capture=False):
    result = subprocess.run(args, text=True, capture_output=capture, check=False)
    if result.returncode:
        raise ValueError(f"failed: {' '.join(args)}" + (f": {result.stderr.strip()}" if capture and result.stderr.strip() else ""))
    return result.stdout.strip() if capture else ""


def enabled():
    names = os.environ.get("AGENTS_HARNESSES", ",".join(HARNESSES)).replace(",", " ").split()
    if not names or len(names) != len(set(names)) or set(names) - set(HARNESSES):
        raise ValueError("AGENTS_HARNESSES must list unique names: pi opencode hermes claude")
    return names


def destinations():
    home = Path.home()
    env = os.environ
    return {
        "pi": Path(env.get("PI_CODING_AGENT_DIR") or home / ".pi/agent"),
        "opencode": Path(env.get("OPENCODE_CONFIG_DIR") or env.get("OPENCODE_DIR") or
                         Path(env.get("XDG_CONFIG_HOME") or home / ".config") / "opencode"),
        "hermes": Path(env.get("HERMES_HOME") or home / ".hermes"),
        "claude": Path(env.get("CLAUDE_CONFIG_DIR") or home / ".claude"),
    }


def validate_prompts():
    source = Path.home() / "profile/prompts"
    if source.is_symlink() and not source.is_dir() or source.exists() and not source.is_dir():
        raise ValueError(f"personal prompts root is not a directory: {source}")
    # All configured adapters use the same portable prompt contract.
    for name, relative in [("pi", "prompts"), ("opencode", "commands"), ("claude", "commands")]:
        run("bash", "-c", 'source "$1"; validate_shared_prompts "$2" "$3"',
            "bash", str(ROOT / "lib/shared-prompts.sh"), str(source), str(ROOT / name / relative))


def native_collisions(names, entries):
    shared = {entry["name"] for entry in entries} | set(skills["personal_skills"]())
    for name in names:
        if name == "claude":
            continue  # Its adapter distinguishes managed links from native entries.
        root = destinations()[name] / "skills"
        for path in set(root.rglob("SKILL.md")) | set(root.glob("*/SKILL.md")):
            match = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", path.read_text(), re.MULTILINE)
            declared = match[1] if match else path.parent.name
            if declared in shared:
                raise ValueError(f"{name}: native/shared skill name collision: {declared} at {path}")


def preflight(names):
    manifest = skills["declarations"](ROOT / "skills.json")
    entries = skills["locked_entries"](manifest)
    skills["collisions"](entries)
    validate_prompts()
    for name in names:
        run(str(ROOT / name / "bootstrap"), "--check")
    native_collisions(names, entries)
    return entries


def contains(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and contains(actual[key], value) for key, value in expected.items()
        )
    return actual == expected


def verify(name, destination):
    """Check declared files and merged settings, not auth or network services."""
    source = ROOT / name
    if name == "claude":
        run(str(source / "bootstrap"), "--verify")
        return
    if name == "hermes":
        actual = json.loads(run("yq", "-o=json", ".", str(destination / "config.yaml"), capture=True))
        expected = json.loads(run("yq", "-o=json", ".", str(source / "config.yaml"), capture=True))
        plain = ["SOUL.md"]
    else:
        config = "settings.json" if name == "pi" else "opencode.json"
        actual = json.loads((destination / config).read_text())
        expected = json.loads((source / config).read_text())
        plain = (["AGENTS.md", "keybindings.json", "mcp.json", "models.json", "pi-fff.json", "settings-extensions.json"]
                 if name == "pi" else ["AGENTS.md", "dcp.jsonc", "notification-ntfy.json", "tui.json"])
        relative = "prompts" if name == "pi" else "commands"
        for prompt in (Path.home() / "profile/prompts").glob("*.md"):
            if (destination / relative / prompt.name).read_bytes() != prompt.read_bytes():
                raise ValueError(f"{name}: prompt differs: {prompt.name}")
        for relative in (["extensions", "prompts", "themes"] if name == "pi" else ["agents", "commands", "themes"]):
            plain.extend(str(p.relative_to(source)) for p in (source / relative).rglob("*") if p.is_file())
    if not contains(actual, expected):
        raise ValueError(f"{name}: runtime config does not contain declared settings")
    for relative in plain:
        target = destination / relative
        if target.is_symlink() or target.read_bytes() != (source / relative).read_bytes():
            raise ValueError(f"{name}: deployment mismatch: {target}")


def apply():
    names = enabled()
    entries = preflight(names)
    try:
        skills["check_tree"](entries)
    except (OSError, ValueError):
        print("Rebuilding community skills from skills.lock", flush=True)
        # Fetch and validate the entire staged tree before replacing existing state.
        skills["realize"](entries, update=False)
    skills["check_tree"](entries)
    for name in names:
        run(str(ROOT / name / "bootstrap"))
        verify(name, destinations()[name])
        print(f"{name}: applied", flush=True)


def sync():
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    # Refuse ambiguity before fetching. Never stash, reset, rebase, or merge.
    branch = run("git", "-C", str(ROOT), "symbolic-ref", "--quiet", "--short", "HEAD", capture=True)
    if run("git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all", capture=True):
        raise ValueError("sync refuses a dirty working tree")
    gitdir = Path(run("git", "-C", str(ROOT), "rev-parse", "--absolute-git-dir", capture=True))
    if any((gitdir / p).exists() for p in ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"]):
        raise ValueError("sync refuses an in-progress Git operation")
    upstream = run("git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "@{upstream}", capture=True)
    run("git", "-C", str(ROOT), "merge-base", "--is-ancestor", "HEAD", upstream, capture=True)
    print(f"Updating {branch} from {upstream} (fast-forward only)", flush=True)
    run("git", "-C", str(ROOT), "pull", "--ff-only")
    # Run the newly pulled entrypoint, not this process's old Python code.
    os.execv(str(ROOT / "agents"), [str(ROOT / "agents"), "apply"])


def doctor():
    failures = []

    def report(label, action):
        try:
            detail = action()
            print(f"OK {label}" + (f": {detail}" if detail else ""))
        except (OSError, ValueError) as error:
            failures.append(label)
            print(f"FAIL {label}: {error}")

    # Disable optional Git index refresh locks so even diagnostics remain read-only.
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    print(f"Repository: {ROOT}")
    report("revision", lambda: run("git", "-C", str(ROOT), "rev-parse", "--short", "HEAD", capture=True))
    report("branch", lambda: run("git", "-C", str(ROOT), "symbolic-ref", "--quiet", "--short", "HEAD", capture=True))
    report("working tree", lambda: run("git", "-C", str(ROOT), "status", "--porcelain", capture=True) or "clean")
    entries = []

    def agreement():
        entries.extend(skills["locked_entries"](skills["declarations"](ROOT / "skills.json")))
        return f"{len(entries)} locked community skills"

    report("manifest/lock", agreement)
    report("community tree", lambda: skills["check_tree"](entries))
    for relative in ["skills", "prompts"]:
        path = Path.home() / "profile" / relative
        print(f"Personal {relative}: {path} ({'present' if path.is_dir() else 'absent; optional'})")
    report("personal layouts and duplicate names", lambda: skills["collisions"](entries))
    report("personal prompts", validate_prompts)
    report("native/shared skill names", lambda: native_collisions(enabled(), entries))
    report("enabled harnesses", lambda: ", ".join(enabled()))
    for command in ["git", "bash", "python3", "jq", "yq", "cp", "cmp", "mktemp"]:
        report(f"dependency {command}", lambda command=command: shutil.which(command) or missing(command))
    for name in enabled():
        destination = destinations()[name]
        print(f"{name} destination: {destination}")
        report(f"{name} preflight", lambda name=name: run(str(ROOT / name / "bootstrap"), "--check", capture=True))
        report(f"{name} deployment", lambda name=name, destination=destination: verify(name, destination))
        binary = "hermes" if name == "hermes" else name
        print(f"{name} binary: {shutil.which(binary) or 'not installed; config deployment does not require it'}")
    return bool(failures)


def missing(command):
    raise ValueError(f"missing {command}")


def main():
    parser = argparse.ArgumentParser(description="Apply and diagnose this mutable agent deployment checkout")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["apply", "sync", "doctor"]:
        commands.add_parser(name)
    skill = commands.add_parser("skill", help="list, add, remove, or explicitly update community skills")
    skill.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.command == "skill":
            if not args.arguments or args.arguments[0] not in {"list", "add", "remove", "update"}:
                raise ValueError("use agents skill list|add|remove|update")
            os.execv(str(ROOT / "lib/skills"), [str(ROOT / "lib/skills"), *args.arguments])
        elif args.command == "apply":
            apply()
        elif args.command == "sync":
            sync()
        else:
            raise SystemExit(doctor())
    except (OSError, ValueError) as error:
        parser.exit(1, f"agents: {error}\n")
