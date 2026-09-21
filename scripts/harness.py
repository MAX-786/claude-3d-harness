# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""claude-3d-harness registry engine.

Run with uv so the one dependency resolves itself:

    uv run scripts/harness.py setup                       the whole install on any OS: the steps below plus verify
    uv run scripts/harness.py doctor                      environment checks
    uv run scripts/harness.py verify                      registry vs. the skill library, and the library vs. its checksums
    uv run scripts/harness.py resolve -w product -p standard
    uv run scripts/harness.py list capabilities
    uv run scripts/harness.py where blender-lighting
    uv run scripts/harness.py mcp-config --provider ahujasid --write
    uv run scripts/harness.py install-extension           Blender-side extension of the active MCP provider
    uv run scripts/harness.py outdated                    read-only: is the pinned MCP server behind its latest release?
    uv run scripts/harness.py audit --changed             flag risky patterns in the skill files edited since the last review
    uv run scripts/harness.py checksums --write           record the skill library as reviewed
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(os.path.abspath(__file__)).parents[1]
REG = ROOT / "registry"
LIB = ROOT / "library"
SUMS = LIB / "SHA256SUMS"  # `sha256sum -c` format, so the library can be checked without this script
ENTRY_SKILL = ROOT / "SKILL.md"  # plugin root: a lone SKILL.md is invoked as /claude-3d-harness
PROJECT_SKILL = ROOT / ".claude" / "skills" / "blender-harness" / "SKILL.md"  # pointer for clones
PLUGIN_DIR = ROOT / ".claude-plugin"
LESSONS = ROOT / "notes" / "lessons.md"
STATUSES = {"active", "chained", "excluded"}


# --------------------------------------------------------------------- loading
def load_yaml(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"cannot load {path.relative_to(ROOT).as_posix()}: {' '.join(str(exc).split())}")


class Registry:
    def __init__(self) -> None:
        self.libraries: dict = load_yaml(REG / "libraries.yaml")["libraries"]
        for lib in self.libraries.values():  # an unquoted all-digit commit id would load as a number
            lib["imported_at"] = str(lib["imported_at"])
        self.skills: dict = load_yaml(REG / "skills.yaml")["skills"]
        self.capabilities: dict = load_yaml(REG / "capabilities.yaml")["capabilities"]
        prof = load_yaml(REG / "profiles.yaml")
        self.profile_order: list = prof["order"]
        self.profiles: dict = prof["profiles"]
        self.mcp: dict = load_yaml(REG / "mcp.yaml")
        self.workflows: dict = {p.stem: load_yaml(p) for p in sorted((ROOT / "workflows").glob("*.yaml"))}

    def skill_relpath(self, sid: str) -> Path:
        key, _, name = sid.partition("/")
        return Path(LIB.name) / key / (self.skills[sid].get("path") or f"{name}/SKILL.md")

    def providers_of(self, cap: str) -> list[str]:
        c = self.capabilities[cap]
        direct = [c["provider"]] if "provider" in c else [v["provider"] for v in c.get("variants", {}).values()]
        return direct + list(c.get("fallbacks", []))

    def mcp_entry(self, provider: str) -> dict:
        launch = self.mcp["providers"][provider]["launch"]
        entry = {"command": launch["command"], "args": list(launch["args"])}
        if launch.get("env"):
            entry["env"] = dict(launch["env"])
        return entry

    def active_mcp(self) -> str | None:
        """Provider whose launch spec matches the server currently in .mcp.json."""
        try:
            servers = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
            current = servers[self.mcp["server_name"]]
        except (OSError, KeyError, ValueError):
            return None
        for name in self.mcp["providers"]:
            want = self.mcp_entry(name)
            if (current.get("command"), current.get("args")) == (want["command"], want["args"]):
                return name
        return None


def rel(p: Path) -> str:
    return p.as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def library_files() -> dict[str, Path]:
    """Every file of the skill library except the checksum list, keyed by its path relative to library/."""
    files = {rel(f.relative_to(LIB)): f for f in LIB.rglob("*") if f.is_file() and f != SUMS}
    return dict(sorted(files.items()))


def recorded_sums() -> dict[str, str]:
    """library/SHA256SUMS as {path relative to library/: digest}; empty when the file is missing."""
    try:
        lines = SUMS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    pairs = (ln.split(maxsplit=1) for ln in lines if ln.strip())
    return {name.lstrip("*"): digest for digest, name in pairs}


def changed_files() -> dict[str, str]:
    """Library files that differ from the recorded checksums: {path: modified | not recorded | missing}."""
    recorded, files = recorded_sums(), library_files()
    state = {name: "not recorded" if name not in recorded else "modified"
             for name, f in files.items() if recorded.get(name) != sha256(f)}
    state.update({name: "missing" for name in recorded if name not in files})
    return dict(sorted(state.items()))


def harness_version() -> str:
    try:
        return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


# "- **cc/blender-lighting (via Cycles) — light linking from Python.** text", or "- **title.** text" for any skill
LESSON = re.compile(r"^- \*\*(?:(?P<skill>[a-z0-9]+/[\w.-]+)(?: \([^)]*\))?\s[—–-]\s)?(?P<title>.+?)\.?\*\*")


def load_lessons() -> list[dict]:
    """The entries of notes/lessons.md, so a load plan can name the ones that concern its skills."""
    try:
        lines = LESSONS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found = ((i, LESSON.match(ln)) for i, ln in enumerate(lines, 1))
    return [{"skill": m.group("skill"), "line": i, "title": m.group("title")} for i, m in found if m]


class Report:
    def __init__(self) -> None:
        self.counts = {"FAIL": 0, "WARN": 0}

    def line(self, level: str, msg: str) -> None:
        if level in self.counts:
            self.counts[level] += 1
        print(f"[{level:<4}] {msg}")

    def finish(self, what: str, strict: bool = False) -> int:
        f, w = self.counts["FAIL"], self.counts["WARN"]
        bad = bool(f or (strict and w))
        print(f"\n{what}: {'FAILED' if bad else 'ok'} ({f} failure(s), {w} warning(s))")
        return 1 if bad else 0


# ---------------------------------------------------------------------- verify
def cmd_verify(reg: Registry, args) -> int:
    r = Report()
    present = {k: (LIB / k).is_dir() and any((LIB / k).iterdir()) for k in reg.libraries}

    for key, lib in reg.libraries.items():
        if lib.get("dialect") not in reg.mcp["dialects"]:
            r.line("FAIL", f"library {key}: unknown dialect '{lib.get('dialect')}'")
        if lib.get("license") == "permission":  # not an open license: say on what basis the files are here, every time
            if not lib.get("license_note"):
                r.line("FAIL", f"library {key}: license is 'permission' but no license_note says who gave it and what it covers")
            else:
                r.line("INFO", f"library {key}: {' '.join(lib['license_note'].split())}")
        elif not lib.get("license") or lib["license"] == "NONE":
            r.line("FAIL", f"library {key}: no license recorded; only vendor what a license or a permission lets you copy")
        if not present[key]:
            r.line("FAIL", f"library {key}: {rel(LIB.relative_to(ROOT))}/{key} is missing or empty - restore it from git, or reinstall the plugin")
        elif not (LIB / key / "LICENSE").is_file():  # a vendored library ships with the terms it was published under
            r.line("FAIL", f"library {key}: {rel(LIB.relative_to(ROOT))}/{key}/LICENSE is missing; its {lib.get('license')} license requires the notice")
    if LIB.is_dir():
        for d in sorted(p.name for p in LIB.iterdir() if p.is_dir() and p.name not in reg.libraries):
            r.line("FAIL", f"library/{d} has no entry in registry/libraries.yaml (origin, commit and license are required)")

    # the library as last reviewed: an edit shows up here until `checksums --write` records it
    if not SUMS.is_file():
        r.line("FAIL", f"{rel(SUMS.relative_to(ROOT))} is missing - after reviewing the library run: harness.py checksums --write")
    else:
        for name, state in changed_files().items():
            r.line("FAIL", f"library/{name}: {state} since the checksums were recorded - review it (harness.py audit --changed), "
                           f"then run: harness.py checksums --write")

    # catalog entries
    by_library: dict[str, set[str]] = {k: set() for k in reg.libraries}
    for sid, e in reg.skills.items():
        key = sid.partition("/")[0]
        if key not in reg.libraries:
            r.line("FAIL", f"skill {sid}: unknown library key '{key}'")
            continue
        if e.get("status") not in STATUSES:
            r.line("FAIL", f"skill {sid}: status must be one of {sorted(STATUSES)}")
        if e.get("status") == "excluded" and not e.get("reason"):
            r.line("FAIL", f"skill {sid}: excluded without a reason")
        if e.get("status") == "chained" and reg.skills.get(e.get("via"), {}).get("status") != "active":
            r.line("FAIL", f"skill {sid}: chained via '{e.get('via')}', which is not an active skill")
        for prov in e.get("requires", {}).get("mcp", []):
            if prov not in reg.mcp["providers"]:
                r.line("FAIL", f"skill {sid}: requires unknown MCP provider '{prov}'")
        path = reg.skill_relpath(sid)
        by_library[key].add(rel(path))
        if present[key] and not (ROOT / path).is_file():
            r.line("FAIL", f"skill {sid}: missing file {rel(path)}")

    # drift: SKILL.md files in the library that the catalog does not know
    for key in reg.libraries:
        for f in sorted((LIB / key).rglob("SKILL.md")) if present[key] else []:
            p = rel(f.relative_to(ROOT))
            if p not in by_library[key]:
                r.line("WARN", f"drift: {p} is in the library but is not cataloged in registry/skills.yaml")

    # capabilities
    referenced: set[str] = set()
    for cap, c in reg.capabilities.items():
        if ("provider" in c) == ("variants" in c):
            r.line("FAIL", f"capability {cap}: needs exactly one of `provider` or `variants`")
            continue
        if "variants" in c and c.get("default") not in c["variants"]:
            r.line("FAIL", f"capability {cap}: default variant '{c.get('default')}' is not defined")
        for sid in reg.providers_of(cap):
            referenced.add(sid)
            status = reg.skills.get(sid, {}).get("status")
            if status != "active":
                r.line("FAIL", f"capability {cap}: '{sid}' is {status or 'not cataloged'}; providers and fallbacks must be active")
    for sid, e in reg.skills.items():
        if e.get("status") == "active" and sid not in referenced:
            r.line("WARN", f"skill {sid}: active but no capability routes to it")

    # profiles and workflows
    if set(reg.profile_order) != set(reg.profiles):
        r.line("FAIL", "profiles.yaml: `order` and `profiles` keys differ")
    for name, p in reg.profiles.items():
        for cap in p.get("always", []):
            if cap not in reg.capabilities:
                r.line("FAIL", f"profile {name}: unknown capability '{cap}' in always")
    for name, wf in reg.workflows.items():
        if wf.get("name") != name:
            r.line("FAIL", f"workflow {name}: `name` field does not match the file name")
        ids = [s["id"] for s in wf.get("stages", [])]
        if len(ids) != len(set(ids)):
            r.line("FAIL", f"workflow {name}: duplicate stage ids")
        for s in wf.get("stages", []) + wf.get("alternatives", []):
            if s["capability"] not in reg.capabilities:
                r.line("FAIL", f"workflow {name}: unknown capability '{s['capability']}'")
            if s.get("min_profile", reg.profile_order[0]) not in reg.profiles:
                r.line("FAIL", f"workflow {name}: unknown min_profile '{s.get('min_profile')}'")
            if s.get("optional") and not s.get("when"):
                r.line("FAIL", f"workflow {name}: optional stage '{s.get('id')}' has no `when`")

    # MCP: one server, canonical name, generated from mcp.yaml
    try:
        servers = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {})
    except (OSError, ValueError):
        servers = None
    if servers is None:
        r.line("FAIL", ".mcp.json missing or unreadable - run: harness.py mcp-config --write")
    else:
        if list(servers) != [reg.mcp["server_name"]]:
            r.line("FAIL", f".mcp.json must define exactly one server named '{reg.mcp['server_name']}', found {list(servers)}")
        active = reg.active_mcp()
        if not active:
            r.line("WARN", ".mcp.json launch spec matches no provider in registry/mcp.yaml - run: harness.py mcp-config --write")
        elif servers.get(reg.mcp["server_name"]) != reg.mcp_entry(active):
            r.line("WARN", f".mcp.json differs from registry/mcp.yaml for '{active}' - run: harness.py mcp-config --provider {active} --write")
        else:
            r.line("INFO", f"MCP provider: {active} as server '{reg.mcp['server_name']}'")

    # entry skill must name every workflow and profile it can choose from
    if ENTRY_SKILL.is_file():
        text = ENTRY_SKILL.read_text(encoding="utf-8")
        for word in [*reg.workflows, *reg.profiles]:
            if not re.search(rf"\b{re.escape(word)}\b", text, re.I):
                r.line("WARN", f"entry skill never mentions '{word}'")
    else:
        r.line("FAIL", f"entry skill missing: {rel(ENTRY_SKILL.relative_to(ROOT))}")

    # plugin packaging: one plugin, one root skill, names that agree
    try:
        plugin = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((PLUGIN_DIR / "marketplace.json").read_text(encoding="utf-8"))
        m = re.search(r"^name:\s*(\S+)", ENTRY_SKILL.read_text(encoding="utf-8"), re.M) if ENTRY_SKILL.is_file() else None
        entries = [p for p in market.get("plugins", []) if p.get("source") in ("./", ".")]
        if not entries or entries[0].get("name") != plugin.get("name"):
            r.line("FAIL", ".claude-plugin/marketplace.json must list this plugin with source './' under the name in plugin.json")
        if not m or m.group(1) != plugin.get("name"):
            r.line("FAIL", f"SKILL.md frontmatter name must equal the plugin name '{plugin.get('name')}' so the command is /{plugin.get('name')}")
    except (OSError, ValueError) as exc:
        r.line("FAIL", f".claude-plugin manifests missing or unreadable: {exc}")
    if (ROOT / "skills").exists():
        r.line("FAIL", "a skills/ directory at the root turns the root SKILL.md into a namespaced skill set; keep the entry skill at SKILL.md")
    if not PROJECT_SKILL.is_file():
        r.line("WARN", f"project entry skill missing: {rel(PROJECT_SKILL.relative_to(ROOT))} (used when the repository is opened as a project)")

    # a lesson filed under a skill id the catalog does not know would never reach a load plan
    for lesson in load_lessons():
        if lesson["skill"] and lesson["skill"] not in reg.skills:
            r.line("WARN", f"{rel(LESSONS.relative_to(ROOT))}:{lesson['line']}: lesson names '{lesson['skill']}', which is not a cataloged skill id")

    names: dict[str, list[str]] = {}
    for sid, e in reg.skills.items():
        if e.get("status") != "excluded" and e.get("kind", "skill") == "skill":
            names.setdefault(sid.partition("/")[2], []).append(sid)
    for name, sids in names.items():
        if len(sids) > 1:
            r.line("INFO", f"name collision kept apart by the registry: {', '.join(sids)}")

    n = {s: sum(1 for e in reg.skills.values() if e.get("status") == s) for s in sorted(STATUSES)}
    print(f"\ncatalog: {len(reg.skills)} entries ({n}), {len(reg.capabilities)} capabilities, "
          f"{len(reg.workflows)} workflows, {len(reg.profiles)} profiles")
    return r.finish("verify", getattr(args, "strict", False))


# --------------------------------------------------------------------- resolve
def pick(reg: Registry, cap: str, variant: str | None, active: str | None):
    """Return (chosen skill id or None, variant used, reasons for skipped candidates)."""
    c = reg.capabilities[cap]
    if "variants" in c:
        variant = variant or c["default"]
        if variant not in c["variants"]:
            raise SystemExit(f"capability {cap}: unknown variant '{variant}' (have: {', '.join(c['variants'])})")
        candidates = [c["variants"][variant]["provider"]]
    else:
        candidates, variant = [c["provider"]], None
    skipped = []
    for sid in candidates + list(c.get("fallbacks", [])):
        needs = reg.skills[sid].get("requires", {}).get("mcp")
        if needs and active and active not in needs:
            skipped.append(f"{sid} needs MCP {'/'.join(needs)}")
        elif not (ROOT / reg.skill_relpath(sid)).is_file():
            skipped.append(f"{sid} file missing")
        else:
            return sid, variant, skipped
    return None, variant, skipped


def missing_libraries(reg: Registry) -> list[str]:
    return [f"{LIB.name}/{k}" for k in reg.libraries if not ((LIB / k).is_dir() and any((LIB / k).iterdir()))]


def cmd_resolve(reg: Registry, args) -> int:
    if missing_libraries(reg):
        raise SystemExit(f"the skill library is incomplete ({', '.join(missing_libraries(reg))}). It ships with the "
                         f"harness: restore it from git, or reinstall the plugin.")
    if args.profile not in reg.profiles:
        raise SystemExit(f"unknown profile '{args.profile}' (have: {', '.join(reg.profile_order)})")
    if bool(args.workflow) == bool(args.capabilities):
        raise SystemExit("give either --workflow or --capabilities")
    if args.workflow and args.workflow not in reg.workflows:
        raise SystemExit(f"unknown workflow '{args.workflow}' (have: {', '.join(reg.workflows)})")
    rank = reg.profile_order.index
    profile = reg.profiles[args.profile]
    active = reg.active_mcp() or reg.mcp["default_provider"]
    variants = dict(v.split("=", 1) for v in args.variant)

    stages: list[dict] = [{"id": "always", "capability": c} for c in profile.get("always", [])]
    alternatives: list[dict] = []
    if args.workflow:
        wf = reg.workflows[args.workflow]
        stages += [s for s in wf["stages"] if rank(s.get("min_profile", reg.profile_order[0])) <= rank(args.profile)]
        alternatives = wf.get("alternatives", [])
    else:
        stages += [{"id": c, "capability": c} for c in args.capabilities]
    for extra in args.add:
        cap, _, var = extra.partition(":")
        if var:
            variants[cap] = var
        stages.append({"id": f"added:{cap}", "capability": cap})
    for s in stages:
        if s["capability"] not in reg.capabilities:
            raise SystemExit(f"unknown capability '{s['capability']}' (see: harness.py list capabilities)")

    seen: dict[str, int] = {}
    rows, optional, used, problems = [], [], [], []
    for s in stages:
        cap = s["capability"]
        sid, variant, skipped = pick(reg, cap, variants.get(cap), active)
        if skipped:
            problems.append(f"{cap}: " + "; ".join(skipped) + (f" -> using {sid}" if sid else " -> UNAVAILABLE"))
        if not sid:
            continue
        used.append(sid)
        c = reg.capabilities[cap]
        label = f"{cap}:{variant}" if variant else cap
        line = {"stage": s["id"], "cap": label, "sid": sid, "path": rel(reg.skill_relpath(sid)),
                "note": s.get("note"), "when": s.get("when"),
                "variants": {k: v["when"] for k, v in c.get("variants", {}).items()} if "variants" in c and cap not in variants else None}
        if s.get("optional"):
            optional.append(line)
        elif sid in seen:
            rows[seen[sid]]["stage"] += f", {s['id']}"
        else:
            seen[sid] = len(rows)
            rows.append(line)

    lessons = [x for x in load_lessons() if x["skill"] is None or x["skill"] in used]
    if args.json:
        print(json.dumps({"workflow": args.workflow, "profile": args.profile, "mcp": active, "root": rel(ROOT),
                          "budgets": profile["budgets"], "load": rows, "optional": optional, "problems": problems,
                          "lessons": lessons}, indent=2))
        return 0

    def tags(sid: str) -> str:
        lib = reg.libraries[sid.partition("/")[0]]
        t = [f"lang:{lib['language']}"] if lib["language"] != "en" else []
        if reg.mcp["dialects"][lib["dialect"]]["map"]:
            t.append(f"dialect:{lib['dialect']}")
        return f"  [{' '.join(t)}]" if t else ""

    prefix = f"mcp__{reg.mcp['server_name']}__"
    print(f"LOAD PLAN  workflow={args.workflow or '(ad hoc)'}  profile={args.profile}  mcp={active}  tools={prefix}<tool>")
    print(f"root: {rel(ROOT)}   (paths below are relative to it)\n")
    print("BUDGETS")
    for k, v in profile["budgets"].items():
        print(f"  {k}: {v}")
    print("\nLOAD IN ORDER (read each SKILL.md just before its stage, not all up front)")
    for i, row in enumerate(rows, 1):
        print(f"  {i:>2}. [{row['stage']}] {row['cap']} -> {row['sid']}{tags(row['sid'])}\n      {row['path']}")
        if row["variants"]:
            print("      variants (choose with --variant): " + "; ".join(f"{k} = {w}" for k, w in row["variants"].items()))
        if row["note"]:
            print(f"      stage note: {row['note']}")
    if optional:
        print("\nOPTIONAL STAGES (include only when the condition holds)")
        for row in optional:
            needs = reg.skills[row["sid"]].get("requires", {}).get("env", [])
            gate = "".join(f"  (needs env {v}: {'set' if os.environ.get(v) else 'NOT SET'})" for v in needs)
            print(f"   - [{row['stage']}] {row['cap']} -> {row['sid']}{tags(row['sid'])}{gate}\n      when: {row['when']}\n      {row['path']}")
            if row["variants"]:
                print("      variants: " + "; ".join(f"{k} = {w}" for k, w in row["variants"].items()))
    if alternatives:
        print("\nALTERNATIVES (re-run resolve with --add <capability> when the condition holds)")
        for a in alternatives:
            print(f"   - {a['capability']}: {a['when']}")

    required = [row["sid"] for row in rows]
    print("\nADAPTATION NOTES (for the skills in LOAD IN ORDER; resolve an optional capability with --add to get its notes)")
    for key in dict.fromkeys(s.partition("/")[0] for s in required):
        lib = reg.libraries[key]
        d = reg.mcp["dialects"][lib["dialect"]]
        if lib.get("notes"):
            print(f"  [{key}] {' '.join(lib['notes'].split())}")
        if d["map"]:
            print(f"  [{key}] tool dialect '{lib['dialect']}': {d['summary']} Translate:")
            for src, dst in d["map"].items():
                dst = " ".join(str(dst).split())
                print(f"      {d['prefix']}{src} -> {prefix + dst if dst in reg.mcp['canonical_tools'] else dst}")
            if d.get("also"):
                print(f"      {' '.join(d['also'].split())}")
    for sid in required:
        e = reg.skills[sid]
        if e.get("notes"):
            print(f"  [{sid}] {' '.join(e['notes'].split())}")
        req = e.get("requires", {})
        for b in req.get("bins", []):
            if not shutil.which(b):
                print(f"  [{sid}] needs `{b}` on PATH: MISSING")
        for v in req.get("env", []):
            print(f"  [{sid}] needs env {v}: {'set' if os.environ.get(v) else 'NOT SET - skip this skill and tell the user'}")
    for key in dict.fromkeys(s.partition("/")[0] for s in required if reg.skills[s].get("requires", {}).get("python")):
        deps = " ".join(f"--with {d}" for d in reg.libraries[key].get("python_deps", []))
        print(f"  [{key}] bundled Python scripts need third-party packages. Run them as: uv run {deps} python <script> ...")
    if problems:
        print("\nSUBSTITUTIONS")
        for p in problems:
            print(f"  {p}")
    fallbacks = {c: reg.capabilities[c].get("fallbacks") for c in (row["cap"].split(":")[0] for row in rows)}
    if any(fallbacks.values()):
        print("\nFALLBACKS (only if the chosen skill is missing or has failed twice on the same defect)")
        for cap, sids in sorted((c, s) for c, s in fallbacks.items() if s):
            print(f"  {cap}: " + ", ".join(f"{s} ({rel(reg.skill_relpath(s))})" for s in sids))
    if lessons:
        print(f"\nLESSONS FROM EARLIER JOBS ({rel(LESSONS.relative_to(ROOT))}; read an entry at its line before the stage that uses the skill)")
        for sid in [*dict.fromkeys(used), None]:
            mine = [x for x in lessons if x["skill"] == sid]
            if mine:
                print(f"  {sid or 'any skill'}")
                for x in mine:
                    print(f"    L{x['line']:<4} {x['title']}")
    return 0


# ------------------------------------------------------------- list and where
def cmd_list(reg: Registry, args) -> int:
    what = args.what
    if what == "libraries":
        for k, lib in reg.libraries.items():
            n = sum(1 for s in reg.skills if s.startswith(k + "/"))
            print(f"{k:<6} {lib['license']:<11} {n:>2} entries  imported from {lib['origin']} at {lib['imported_at'][:12]}")
    elif what == "skills":
        for sid, e in reg.skills.items():
            print(f"{e['status']:<9} {sid:<34} {e.get('summary', '')}")
    elif what == "capabilities":
        for cap, c in reg.capabilities.items():
            prov = c.get("provider") or "{" + ", ".join(f"{k}: {v['provider']}" for k, v in c["variants"].items()) + "}"
            fb = f"  (fallbacks: {', '.join(c['fallbacks'])})" if c.get("fallbacks") else ""
            print(f"{cap:<26} {prov}{fb}\n{'':<26} {c['summary']}")
    elif what == "workflows":
        for name, wf in reg.workflows.items():
            print(f"{name:<12} {wf['summary']}\n{'':<12} match: {' | '.join(wf['match'])}")
    elif what == "profiles":
        for name in reg.profile_order:
            p = reg.profiles[name]
            print(f"{name:<10} {p['summary']}\n{'':<10} signals: {' | '.join(p['signals'])}")
    return 0


def cmd_where(reg: Registry, args) -> int:
    hits = [sid for sid in reg.skills if sid.partition("/")[2] == args.name or sid == args.name]
    if not hits:
        print(f"no cataloged skill named '{args.name}'")
        return 1
    for sid in hits:
        e = reg.skills[sid]
        routes = [c for c in reg.capabilities if sid in reg.providers_of(c)]
        extra = f"via {e['via']}" if e.get("via") else f"excluded: {e['reason']}" if e.get("reason") else f"capabilities: {', '.join(routes) or '-'}"
        print(f"{sid}  [{e['status']}]  {extra}\n  {rel(reg.skill_relpath(sid))}")
    if len(hits) > 1:
        print("\nSeveral libraries use this name. Inside a library skill, a bare name means the sibling in the SAME library.")
    return 0


# ------------------------------------------------------------------ mcp-config
def cmd_mcp_config(reg: Registry, args) -> int:
    provider = args.provider or reg.active_mcp() or reg.mcp["default_provider"]
    if provider not in reg.mcp["providers"]:
        raise SystemExit(f"unknown provider '{provider}' (have: {', '.join(reg.mcp['providers'])})")
    text = json.dumps({"mcpServers": {reg.mcp["server_name"]: reg.mcp_entry(provider)}}, indent=2) + "\n"
    if args.write:
        (ROOT / ".mcp.json").write_text(text, encoding="utf-8", newline="\n")
        print(f".mcp.json written for provider '{provider}' (server name '{reg.mcp['server_name']}'). Restart Claude Code to pick it up.")
    else:
        print(text, end="")
    return 0


# ----------------------------------------------------------- install-extension
def cmd_install_extension(reg: Registry, args) -> int:
    import urllib.request

    provider = reg.active_mcp() or reg.mcp["default_provider"]
    info = reg.mcp["providers"][provider]
    ext = info.get("blender_extension")
    if not ext:
        print(f"Provider '{provider}' has no packaged extension. Install its add-on by hand:\n  {info.get('blender_addon')}\n  {' '.join(info['notes'].split())}")
        return 0

    need = tuple(map(int, info["blender_min"].split(".")))
    blenders = []
    for exe in ([args.blender] if args.blender else find_blender()):
        v = blender_version(exe)
        if v is not None and v[:2] < need:
            print(f"skipping {exe}: Blender {'.'.join(map(str, v))} is older than {info['blender_min']}")
        else:
            blenders.append(exe)
    if not blenders:
        print(f"No Blender >= {info['blender_min']} found. Install it from https://www.blender.org/download/ and re-run, "
              f"or pass --blender <path to blender executable>.")
        return 1
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    target = cache / ext["url"].rsplit("/", 1)[1]
    if not target.is_file() or sha256(target) != ext["sha256"]:
        print(f"downloading {ext['url']}")
        try:
            urllib.request.urlretrieve(ext["url"], target)
        except OSError as exc:  # URLError included: offline, proxy, release asset moved
            print(f"download failed: {exc}. Nothing was installed.")
            return 1
    if sha256(target) != ext["sha256"]:
        target.unlink()
        raise SystemExit("checksum mismatch for the downloaded extension - nothing was installed")
    print(f"checksum ok: {target.name}")
    for exe in blenders:
        print(f"installing into {exe}")
        done = subprocess.run([exe, "--command", "extension", "install-file", "-r", "user_default", "-e", str(target)])
        if done.returncode:
            print(f"  Blender exited with {done.returncode}. Install by hand: Edit > Preferences > Add-ons > Install from Disk > {target}")
    print("Open Blender, press N in the 3D View and check the BlenderMCP tab. Then restart Claude Code.")
    return 0


# ----------------------------------------------------------------------- setup
def cmd_setup(reg: Registry, args) -> int:
    """The whole install in one command, the same on every OS. Each step is also a command of its own."""
    print("== 1/3  MCP configuration")
    cmd_mcp_config(reg, argparse.Namespace(provider=args.provider, write=True))
    (ROOT / "output").mkdir(exist_ok=True)  # the MCP server's workspace in a clone
    print("\n== 2/3  Blender extension")
    if args.skip_blender_extension:
        print("skipped (--skip-blender-extension)")
    elif cmd_install_extension(reg, args):
        print("The Blender extension was not installed. Install Blender (or pass --blender <executable>), then re-run setup.")
    print("\n== 3/3  checks")
    status = cmd_doctor(reg, args) | cmd_verify(reg, args)
    print("\nSetup finished with open issues: see the FAIL lines above." if status else
          "\nReady. Start Blender, check the BlenderMCP tab in the 3D View sidebar (N), then open Claude Code in this folder.")
    return status


# -------------------------------------------------------------------- outdated
def fetch_json(url: str) -> dict:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "claude-3d-harness", "Accept": "application/json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):  # the token goes to GitHub and nowhere else
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as fh:
        return json.load(fh)


def cmd_outdated(reg: Registry, args) -> int:
    """Compare the MCP server pins with what is published now. Changes nothing. Exit 3 when a pin is behind.

    The skill library is not checked: it lives in this repository and follows nobody's branch.
    """
    rows, errors = [], []
    for name, p in reg.mcp["providers"].items():
        pypi = next(filter(None, (re.fullmatch(r"([A-Za-z0-9_.-]+)==([\w.]+)", a) for a in p["launch"]["args"])), None)
        try:
            if p.get("release"):
                slug = p["repo"].removeprefix("https://github.com/")
                latest = fetch_json(f"https://api.github.com/repos/{slug}/releases/latest")["tag_name"]
                if latest != p["release"]:
                    rows.append({"what": f"MCP provider {name}", "pinned": p["release"], "latest": latest,
                                 "review": f"{p['repo']}/compare/{p['release']}...{latest}",
                                 "next": "update release, both URLs and both SHA-256 values in registry/mcp.yaml, then: "
                                         "uv run scripts/harness.py mcp-config --write" +
                                         (f". Compare library/{p['library']} with the skills the new release ships"
                                          if p.get("library") else "")})
            elif pypi:
                latest = fetch_json(f"https://pypi.org/pypi/{pypi.group(1)}/json")["info"]["version"]
                if latest != pypi.group(2):
                    rows.append({"what": f"MCP provider {name}", "pinned": pypi.group(2), "latest": latest,
                                 "review": f"https://pypi.org/project/{pypi.group(1)}/{latest}/",
                                 "next": "update the pinned version in registry/mcp.yaml, then: uv run scripts/harness.py mcp-config --write"})
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"MCP provider {name}: could not read the latest version ({exc})")

    if args.markdown:
        if rows:
            print("The pinned MCP server is behind what its project publishes now. Nothing was changed: the server and its "
                  "Blender extension run code on the user's machine, so each move is reviewed by a person.\n")
            print("| Pin | Pinned | Latest | Review |\n| --- | --- | --- | --- |")
            for row in rows:
                print(f"| {row['what']} | `{row['pinned']}` | `{row['latest']}` | [compare]({row['review']}) |")
            print("\nNext steps:\n")
            for row in rows:
                print(f"- **{row['what']}**: {row['next']}")
        else:
            print("Every MCP server pin matches the latest release.")
        if errors:
            print("\nCould not check:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        for row in rows:
            print(f"{row['what']:<24} {row['pinned']} -> {row['latest']}\n    review: {row['review']}\n    next:   {row['next']}")
        for e in errors:
            print(f"could not check: {e}")
        print(f"\noutdated: {len(rows)} pin(s) behind, {len(errors)} check(s) failed" if rows or errors else
              "every MCP server pin matches the latest release")
    return 3 if rows else 1 if errors else 0


# ------------------------------------------------------------------- checksums
def cmd_checksums(reg: Registry, args) -> int:
    """Show which library files differ from library/SHA256SUMS, or record the library as it is now."""
    if args.write:
        files = library_files()
        text = "".join(f"{sha256(f)}  {name}\n" for name, f in files.items())
        SUMS.write_text(text, encoding="utf-8", newline="\n")
        print(f"{rel(SUMS.relative_to(ROOT))} written: {len(files)} file(s). Commit it together with the files you changed.")
        return 0
    changed = changed_files()
    for name, state in changed.items():
        print(f"{state:<13} library/{name}")
    print(f"{len(changed)} file(s) differ from {rel(SUMS.relative_to(ROOT))}. Review them (harness.py audit --changed), then: "
          f"harness.py checksums --write" if changed else f"the library matches {rel(SUMS.relative_to(ROOT))}")
    return 1 if changed else 0


# ----------------------------------------------------------------------- audit
AUDIT = {
    "network call": r"\b(curl|wget|Invoke-WebRequest|Invoke-RestMethod|requests\.(get|post|put)|urllib\.request|urlopen|fetch\(|https?\.request|import socket|socket\.(socket|create_connection)\()",
    "shell or dynamic execution": r"\b(subprocess\.|os\.system|os\.popen|child_process|execSync|spawn\(|eval\(|exec\(|__import__|importlib|pickle\.|marshal\.|ctypes)",
    "secret or credential": r"(?i)(api[_-]?key|access[_-]?token|secret|password|bearer |\.ssh\b|credentials|os\.environ|getenv)",
    "agent or config tampering": r"(?i)(~/\.claude|\.claude/|settings\.json|CLAUDE\.md|\.mcp\.json|dangerously|bypass permission|ignore (all |any )?(previous|prior|above) instructions|do not (tell|inform|mention)[^.\n]{0,40}\buser)",
    "install or persistence": r"(?i)(pip3? install|npm (i|install)\b|npx |claude mcp add|claude plugin|schtasks|crontab|reg add|Set-ExecutionPolicy|ln -s|addon_install|addon_enable|extension_install|use_scripts_auto_execute|driver_namespace)",
    "destructive file operation": r"(?i)(rm -rf|Remove-Item[^\n]*-Recurse|shutil\.rmtree|os\.remove|os\.unlink|fs\.rm|rmdir /s|del /s)",
    "scene or session wipe": r"(read_factory_settings|read_homefile|open_mainfile|save_mainfile|save_as_mainfile|quit_blender|batch_remove|orphans_purge)",
    "skill self-modification": r"(?i)(git (commit|push|tag)|gh (pr|release) create|patch (the|this) skill|update (the|this) SKILL\.md)",
    # zero-width and bidirectional controls, Unicode tag characters, and long base64-looking runs
    "hidden or encoded text": r"[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]|[A-Za-z0-9+/]{120,}={0,2}",
}
AUDIT_EXT = {".md", ".py", ".js", ".mjs", ".ts", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".txt", ".html", ".htm", ".svg"}


def cmd_audit(reg: Registry, args) -> int:
    """Flag lines a reviewer should read. It finds patterns, not intent: a clean audit is not a clean bill of health."""
    keys = args.keys or list(reg.libraries)
    for key in keys:
        if key not in reg.libraries:
            raise SystemExit(f"unknown library '{key}' (have: {', '.join(reg.libraries)})")
    changed = changed_files() if args.changed else None
    total = 0
    for key in keys:
        files = {n: f for n, f in library_files().items() if n.startswith(key + "/") and (changed is None or n in changed)}
        other = sorted(n for n, f in files.items() if f.suffix.lower() not in AUDIT_EXT and f.name != "LICENSE")
        files = {n: f for n, f in files.items() if f.suffix.lower() in AUDIT_EXT}
        print(f"[{key}] {len(files)} file(s) scanned" + (" (changed since the checksums were recorded)" if args.changed else ""))
        for name, f in files.items():
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            for label, pat in AUDIT.items():
                hits = [(i, ln.strip()) for i, ln in enumerate(lines, 1) if re.search(pat, ln)]
                if not hits:
                    continue
                total += len(hits)
                print(f"  {label:<28} library/{name}  x{len(hits)}")
                for i, ln in hits[: (len(hits) if args.verbose else 2)]:
                    if label.startswith("hidden"):  # show what a terminal would not
                        ln = ln.encode("ascii", "backslashreplace").decode()
                    print(f"      {i}: {ln[:150]}")
        if other:
            print(f"  not text, so not scanned: {len(other)} file(s)" + (": " + ", ".join(other) if args.verbose else ""))
    print(f"\n{total} line(s) flagged. Flags are prompts for human review, not verdicts: library skills are "
          f"instructions Claude will follow with code-execution rights inside Blender.")
    return 0


# ---------------------------------------------------------------------- doctor
def find_blender() -> list[str]:
    found = [shutil.which("blender")] if shutil.which("blender") else []
    if os.name == "nt":
        import winreg

        # The installer records its location, which covers other drives and drive-root installs.
        uninstall = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        for hive, sub in ((winreg.HKEY_LOCAL_MACHINE, uninstall), (winreg.HKEY_CURRENT_USER, uninstall),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")):
            try:
                root = winreg.OpenKey(hive, sub)
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(root)[0]):
                try:
                    with winreg.OpenKey(root, winreg.EnumKey(root, i)) as key:
                        if str(winreg.QueryValueEx(key, "DisplayName")[0]).lower().startswith("blender"):
                            found.append(str(Path(winreg.QueryValueEx(key, "InstallLocation")[0]) / "blender.exe"))
                except OSError:
                    continue
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", ""),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
            if base:
                found += [str(p) for p in Path(base).glob("Blender Foundation/Blender*/blender.exe")]
                found += [str(p) for p in Path(base).glob("Steam/steamapps/common/Blender/blender.exe")]
    elif sys.platform == "darwin":
        home = Path.home()
        for base in (Path("/Applications"), home / "Applications",
                     home / "Library" / "Application Support" / "Steam" / "steamapps" / "common" / "Blender"):
            found += [str(p) for p in base.glob("Blender*.app/Contents/MacOS/Blender")]
    else:  # Linux: distro packages and snap are on PATH already; tarballs, Steam and flatpak are not
        home = Path.home()
        for base, pattern in ((Path("/opt"), "blender*/blender"), (Path("/usr/local"), "blender*/blender"),
                              (home, "blender*/blender"), (home / "Applications", "blender*/blender"),
                              (home / ".local" / "share" / "Steam" / "steamapps" / "common", "Blender/blender"),
                              (home / ".steam" / "steam" / "steamapps" / "common", "Blender/blender"),
                              (Path("/var/lib/flatpak/exports/bin"), "org.blender.Blender"),
                              (home / ".local" / "share" / "flatpak" / "exports" / "bin", "org.blender.Blender")):
            found += [str(p) for p in base.glob(pattern)]
    # One entry per real file, but keep the path as found: /snap/bin/blender is a link to the snap launcher itself.
    unique: dict[str, str] = {}
    for f in found:
        if Path(f).is_file():
            unique.setdefault(os.path.realpath(f), f)
    return sorted(unique.values())


def blender_version(exe: str) -> tuple[int, ...] | None:
    """Ask the executable: folder names say nothing for custom or drive-root installs."""
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60,
                             encoding="utf-8", errors="replace").stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"Blender (\d+)\.(\d+)(?:\.(\d+))?", out or "")
    return tuple(int(x) for x in m.groups() if x) if m else None


def blender_config_dir(version: tuple[int, ...], exe: str = "") -> Path:
    name = f"{version[0]}.{version[1]}"
    if exe.endswith("org.blender.Blender"):  # flatpak keeps each app's config under ~/.var/app/<id>
        return Path.home() / ".var" / "app" / "org.blender.Blender" / "config" / "blender" / name
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", "")) / "Blender Foundation" / "Blender" / name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Blender" / name
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "blender" / name


def cmd_doctor(reg: Registry, args) -> int:
    r = Report()
    kind = "plugin install" if "/.claude/plugins/" in rel(ROOT) else "checkout"  # bug reports need to say which
    r.line("INFO", f"claude-3d-harness {harness_version()} ({kind}) on {platform.platform()}, Python {platform.python_version()}")
    r.line("OK" if shutil.which("uv") else "FAIL", f"uv: {shutil.which('uv') or 'not found'} (this script and the MCP server launcher)")
    r.line("OK" if shutil.which("ffmpeg") else "WARN",
           f"ffmpeg: {shutil.which('ffmpeg') or 'not found'} (optional: encoding a rendered frame sequence to video)")
    if os.name == "nt":  # Windows refuses paths over 260 characters unless long paths are enabled system-wide
        deepest = max((len(name) for name in library_files()), default=0) + len(LIB.name) + 1
        n = len(str(ROOT.resolve()))
        r.line("WARN" if n + 1 + deepest >= 260 else "OK",
               f"harness path length: {n} characters (the deepest library file adds {deepest}; keep the total under 260)")
    provider = reg.mcp["providers"][reg.active_mcp() or reg.mcp["default_provider"]]
    need = provider["blender_min"]
    versions = {exe: blender_version(exe) for exe in find_blender()}
    shown = ", ".join(f"{exe} ({'.'.join(map(str, v)) if v else 'version unknown'})" for exe, v in versions.items())
    r.line("OK" if versions else "WARN", f"Blender (>= {need} needed): {shown or 'not found - pass its path: harness.py install-extension --blender <blender executable>'}")
    ext_id = provider.get("blender_extension", {}).get("id")
    for exe, v in versions.items():
        if ext_id and v:
            installed = (blender_config_dir(v, exe) / "extensions" / "user_default" / ext_id).is_dir()
            r.line("OK" if installed else "WARN", f"Blender {v[0]}.{v[1]} extension '{ext_id}': " +
                   ("installed" if installed else "NOT installed, so Blender shows no MCP sidebar tab - run: uv run scripts/harness.py install-extension"))
    missing = missing_libraries(reg)
    r.line("FAIL" if missing else "OK", "skill library: " + (f"missing {', '.join(missing)} - restore it from git, or reinstall the plugin"
                                                           if missing else f"{len(reg.libraries)} libraries, {len(library_files())} files"))
    active = reg.active_mcp()
    r.line("OK" if active else "WARN", f".mcp.json provider: {active or 'none recognised - run harness.py mcp-config --write'}")
    try:  # a second Blender server at user scope would compete for the same Blender instance
        user = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8")).get("mcpServers", {})
        dupes = [k for k in user if "blender" in k.lower()]
        r.line("WARN" if dupes else "OK", "user-scope Blender MCP servers: " +
               (f"{dupes} - remove them (claude mcp remove <name> --scope user) so only the project server runs" if dupes else "none"))
    except (OSError, ValueError):
        pass
    with socket.socket() as s:
        s.settimeout(0.4)
        listening = s.connect_ex(("127.0.0.1", 9876)) == 0
    r.line("INFO", f"Blender addon endpoint 127.0.0.1:9876: {'listening' if listening else 'closed (start Blender and enable the MCP add-on)'}")
    return r.finish("doctor")


# ------------------------------------------------------------------------ main
def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="claude-3d-harness registry engine")
    ap.add_argument("--version", action="version", version=f"claude-3d-harness {harness_version()}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("setup", help="the whole install: mcp-config, install-extension, doctor, verify")
    p.add_argument("--provider", help="MCP provider to configure (default: keep the current one)")
    p.add_argument("--blender", help="path to the blender executable")
    p.add_argument("--skip-blender-extension", action="store_true", help="leave Blender alone")
    sub.add_parser("doctor", help="check tools, Blender and its extension, the skill library, MCP config")
    p = sub.add_parser("verify", help="validate the registry against the skill library, and the library against its checksums")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures (CI)")
    p = sub.add_parser("outdated", help="read-only check: is the pinned MCP server behind its latest release?")
    p.add_argument("--markdown", action="store_true", help="print the report as Markdown (for an issue body)")
    p = sub.add_parser("resolve", help="print the load plan for a job")
    p.add_argument("-w", "--workflow")
    p.add_argument("-c", "--capabilities", nargs="+", default=[])
    p.add_argument("-p", "--profile", default="standard")
    p.add_argument("--add", action="append", default=[], metavar="CAP[:VARIANT]")
    p.add_argument("--variant", action="append", default=[], metavar="CAP=VARIANT")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("list", help="print a registry table")
    p.add_argument("what", choices=["libraries", "skills", "capabilities", "workflows", "profiles"])
    p = sub.add_parser("where", help="find a skill by bare name")
    p.add_argument("name")
    p = sub.add_parser("mcp-config", help="render .mcp.json from registry/mcp.yaml")
    p.add_argument("--provider")
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("audit", help="flag risky patterns in the skill library for human review")
    p.add_argument("keys", nargs="*", help="library keys (default: all)")
    p.add_argument("--changed", action="store_true", help="only the files that differ from library/SHA256SUMS")
    p.add_argument("-v", "--verbose", action="store_true", help="print every flagged line, not the first two per file")
    p = sub.add_parser("checksums", help="compare the skill library with library/SHA256SUMS (exit 1 when it differs)")
    p.add_argument("--write", action="store_true", help="record the library as it is now, after reviewing the changes")
    p = sub.add_parser("install-extension", help="download, checksum and install the Blender-side extension of the active MCP provider")
    p.add_argument("--blender", help="path to the blender executable")
    args = ap.parse_args()
    handler = globals()["cmd_" + args.cmd.replace("-", "_")]
    return handler(Registry(), args)


if __name__ == "__main__":
    sys.exit(main())
