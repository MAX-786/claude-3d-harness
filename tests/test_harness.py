"""Tests for scripts/harness.py.

    uv run --with pytest --with pyyaml pytest -q

Tests that read upstream files skip when the submodules are not checked out
(`uv run scripts/harness.py bootstrap`). Nothing here talks to Blender or the
network: `outdated` runs against stand-ins for its two lookups.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("harness", ROOT / "scripts" / "harness.py")
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

_REG = harness.Registry()
needs_upstreams = pytest.mark.skipif(bool(harness.missing_upstreams(_REG)),
                                     reason="upstream submodules are not checked out")
JOBS = [(w, p) for w in _REG.workflows for p in _REG.profile_order]


@pytest.fixture()
def reg():
    return harness.Registry()


def plan(reg, capsys, **kw) -> dict:
    args = dict(workflow=None, capabilities=[], profile="standard", add=[], variant=[], json=True)
    args.update(kw)
    assert harness.cmd_resolve(reg, argparse.Namespace(**args)) == 0
    return json.loads(capsys.readouterr().out)


# ---------------------------------------------------------------------- verify
@needs_upstreams
def test_the_registry_verifies_without_warnings(reg, capsys):
    assert harness.cmd_verify(reg, argparse.Namespace(strict=True)) == 0, capsys.readouterr().out


def test_warnings_fail_only_in_strict_mode():
    r = harness.Report()
    r.line("WARN", "something to look at")
    assert r.finish("check") == 0
    assert r.finish("check", strict=True) == 1


def test_routing_to_an_excluded_skill_fails_verify(reg, capsys):
    excluded = next(sid for sid, e in reg.skills.items() if e["status"] == "excluded")
    cap = next(c for c, v in reg.capabilities.items() if "provider" in v)
    reg.capabilities[cap]["provider"] = excluded
    assert harness.cmd_verify(reg, argparse.Namespace(strict=False)) == 1
    assert f"capability {cap}: '{excluded}' is excluded" in capsys.readouterr().out


def test_mcp_json_is_what_the_registry_generates(reg, capsys):
    harness.cmd_mcp_config(reg, argparse.Namespace(provider=None, write=False))
    assert capsys.readouterr().out == (ROOT / ".mcp.json").read_text(encoding="utf-8"), \
        ".mcp.json was edited by hand; regenerate it with: harness.py mcp-config --write"


def test_plugin_and_entry_skill_share_one_name():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert f"name: {plugin['name']}" in (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert harness.harness_version() == plugin["version"]


# --------------------------------------------------------------------- resolve
@needs_upstreams
@pytest.mark.parametrize("workflow,profile", JOBS)
def test_every_job_type_resolves_to_files_that_exist(reg, capsys, workflow, profile):
    out = plan(reg, capsys, workflow=workflow, profile=profile)
    assert not [p for p in out["problems"] if "UNAVAILABLE" in p]
    for row in out["load"] + out["optional"]:
        assert (ROOT / row["path"]).is_file(), row
    always = len(reg.profiles[profile]["always"])
    assert [row["stage"].split(",")[0] for row in out["load"][:always]] == ["always"] * always


@needs_upstreams
@pytest.mark.parametrize("workflow", list(_REG.workflows))
def test_a_higher_profile_never_drops_a_skill(reg, capsys, workflow):
    loads = [{row["sid"] for row in plan(reg, capsys, workflow=workflow, profile=p)["load"]} for p in reg.profile_order]
    for lower, higher in zip(loads, loads[1:]):
        assert lower <= higher


@needs_upstreams
def test_an_edit_can_name_capabilities_instead_of_a_workflow(reg, capsys):
    caps = [c for c, v in reg.capabilities.items() if "provider" in v][:2]
    out = plan(reg, capsys, capabilities=caps, profile="fast")
    assert {row["cap"] for row in out["load"]} >= set(caps)


def test_workflow_and_capabilities_are_mutually_exclusive(reg):
    args = argparse.Namespace(workflow=next(iter(reg.workflows)), capabilities=["materials"], profile="fast",
                              add=[], variant=[], json=True)
    if harness.missing_upstreams(reg):
        pytest.skip("upstream submodules are not checked out")
    with pytest.raises(SystemExit, match="either --workflow or --capabilities"):
        harness.cmd_resolve(reg, args)


@needs_upstreams
def test_a_missing_provider_file_falls_back(reg, monkeypatch):
    cap, c = next((k, v) for k, v in reg.capabilities.items() if "provider" in v and v.get("fallbacks"))
    real = reg.skill_relpath
    monkeypatch.setattr(reg, "skill_relpath", lambda sid: Path("missing.md") if sid == c["provider"] else real(sid))
    sid, _, skipped = harness.pick(reg, cap, None, None)
    assert sid == c["fallbacks"][0]
    assert skipped == [f"{c['provider']} file missing"]


def test_an_unknown_variant_is_rejected(reg):
    cap = next(k for k, v in reg.capabilities.items() if "variants" in v)
    with pytest.raises(SystemExit, match="unknown variant"):
        harness.pick(reg, cap, "no-such-variant", None)


# --------------------------------------------------------------------- lessons
LESSONS_MD = """# Lessons

## 2026-01-01 — job x

- **cc/blender-lighting (via Cycles) — light linking from Python.** A receiver collection
  set on a light was not honoured.
- **Poly Haven multi-part models.** Parts carry relative offsets.
- a plain bullet is not a lesson
- **newo/blender-mcp - `result` is not returned.** Only stdout comes back.
"""


def test_lessons_are_parsed_with_skill_line_and_title(tmp_path, monkeypatch):
    path = tmp_path / "lessons.md"
    path.write_text(LESSONS_MD, encoding="utf-8")
    monkeypatch.setattr(harness, "LESSONS", path)
    assert harness.load_lessons() == [
        {"skill": "cc/blender-lighting", "line": 5, "title": "light linking from Python"},
        {"skill": None, "line": 7, "title": "Poly Haven multi-part models"},
        {"skill": "newo/blender-mcp", "line": 9, "title": "`result` is not returned"},
    ]


def test_a_missing_lessons_file_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "LESSONS", tmp_path / "absent.md")
    assert harness.load_lessons() == []


@needs_upstreams
def test_a_load_plan_names_only_the_lessons_for_its_skills(reg, capsys, tmp_path, monkeypatch):
    workflow = next(iter(reg.workflows))
    loaded = {row["sid"] for row in plan(reg, capsys, workflow=workflow, profile="fast")["load"]}
    inside = sorted(loaded)[0]
    outside = next(sid for sid, e in reg.skills.items() if e["status"] == "active" and sid not in loaded)
    path = tmp_path / "lessons.md"
    path.write_text(f"- **{inside} — relevant.** x\n- **{outside} — irrelevant.** x\n- **General.** x\n", encoding="utf-8")
    monkeypatch.setattr(harness, "LESSONS", path)
    titles = [x["title"] for x in plan(reg, capsys, workflow=workflow, profile="fast")["lessons"]]
    assert titles == ["relevant", "General"]


def test_verify_warns_about_a_lesson_for_an_unknown_skill(reg, capsys, tmp_path, monkeypatch):
    path = ROOT / "notes" / "_test_lessons.md"  # verify prints the path relative to the repository
    monkeypatch.setattr(harness, "LESSONS", path)
    path.write_text("- **zz/no-such-skill — typo.** x\n", encoding="utf-8")
    try:
        harness.cmd_verify(reg, argparse.Namespace(strict=False))
    finally:
        path.unlink()
    assert "lesson names 'zz/no-such-skill'" in capsys.readouterr().out


def test_the_shipped_lessons_all_name_cataloged_skills(reg):
    unknown = [x for x in harness.load_lessons() if x["skill"] and x["skill"] not in reg.skills]
    assert harness.load_lessons() and not unknown


# ---------------------------------------------------------------- catalog-bump
def test_catalog_bump_rewrites_only_the_named_upstream(reg, tmp_path, monkeypatch):
    shutil.copy(ROOT / "registry" / "upstreams.yaml", tmp_path / "upstreams.yaml")
    monkeypatch.setattr(harness, "REG", tmp_path)
    monkeypatch.setattr(harness, "git", lambda *a, **k: "f" * 40)
    key, *others = reg.upstreams
    assert harness.cmd_catalog_bump(reg, argparse.Namespace(keys=[key], all=False)) == 0
    after = yaml.safe_load((tmp_path / "upstreams.yaml").read_text(encoding="utf-8"))["upstreams"]
    assert after[key]["cataloged_at"] == "f" * 40
    assert {k: after[k]["cataloged_at"] for k in others} == {k: reg.upstreams[k]["cataloged_at"] for k in others}


# -------------------------------------------------------------------- outdated
def answers(reg, **override):
    """A stand-in for fetch_json that reports every provider at its pinned version, unless overridden."""
    def fetch(url: str) -> dict:
        for name, p in reg.mcp["providers"].items():
            if p.get("release") and p["repo"].removeprefix("https://github.com/") in url:
                return {"tag_name": override.get(name, p["release"])}
        if "pypi.org" in url:
            pin = next(a for p in reg.mcp["providers"].values() for a in p["launch"]["args"] if "==" in a)
            return {"info": {"version": override.get("pypi", pin.split("==")[1])}}
        raise OSError(f"unexpected lookup: {url}")
    return fetch


def tips(reg, **override):
    by_repo = {up["repo"]: override.get(key, up["cataloged_at"]) for key, up in reg.upstreams.items()}
    return lambda repo, branch: by_repo[repo]


def test_outdated_is_quiet_when_every_pin_is_current(reg, capsys, monkeypatch):
    monkeypatch.setattr(harness, "remote_tip", tips(reg))
    monkeypatch.setattr(harness, "fetch_json", answers(reg))
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=False)) == 0
    assert "every pin matches" in capsys.readouterr().out


def test_outdated_reports_a_moved_upstream_with_its_compare_link(reg, capsys, monkeypatch):
    released = {p.get("upstream") for p in reg.mcp["providers"].values() if p.get("release")}
    key = next(k for k in reg.upstreams if k not in released)
    monkeypatch.setattr(harness, "remote_tip", tips(reg, **{key: "a" * 40}))
    monkeypatch.setattr(harness, "fetch_json", answers(reg))
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=True)) == 3
    out = capsys.readouterr().out
    up = reg.upstreams[key]
    assert f"{up['repo']}/compare/{up['cataloged_at'][:12]}...{'a' * 12}" in out
    assert f"harness.py update {key}" in out


def test_outdated_follows_the_release_of_an_mcp_provider_not_its_branch(reg, capsys, monkeypatch):
    name, p = next((n, p) for n, p in reg.mcp["providers"].items() if p.get("release") and p.get("upstream"))
    asked = []
    monkeypatch.setattr(harness, "remote_tip", lambda repo, branch: asked.append(repo) or tips(reg)(repo, branch))
    monkeypatch.setattr(harness, "fetch_json", answers(reg, **{name: "v99.0.0"}))
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=False)) == 3
    assert reg.upstreams[p["upstream"]]["repo"] not in asked
    assert f"{p['release']} -> v99.0.0" in capsys.readouterr().out


def test_outdated_says_so_when_it_could_not_check(reg, capsys, monkeypatch):
    def offline(url):
        raise OSError("offline")
    monkeypatch.setattr(harness, "remote_tip", lambda repo, branch: None)
    monkeypatch.setattr(harness, "fetch_json", offline)
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=False)) == 1
    assert "could not check" in capsys.readouterr().out


# ----------------------------------------------------------------------- setup
def test_setup_runs_the_install_steps_in_order(reg, monkeypatch):
    calls = []
    for name, status in (("bootstrap", 0), ("mcp_config", 0), ("install_extension", 1), ("doctor", 0), ("verify", 0)):
        monkeypatch.setattr(harness, f"cmd_{name}", lambda r, a, n=name, s=status: calls.append(n) or s)
    args = argparse.Namespace(provider=None, blender=None, skip_blender_extension=False)
    assert harness.cmd_setup(reg, args) == 0  # a missing Blender is a hint, not a failed setup
    assert calls == ["bootstrap", "mcp_config", "install_extension", "doctor", "verify"]


def test_setup_can_leave_blender_alone_and_reports_failed_checks(reg, monkeypatch):
    calls = []
    for name, status in (("bootstrap", 0), ("mcp_config", 0), ("install_extension", 0), ("doctor", 1), ("verify", 0)):
        monkeypatch.setattr(harness, f"cmd_{name}", lambda r, a, n=name, s=status: calls.append(n) or s)
    args = argparse.Namespace(provider="ahujasid", blender=None, skip_blender_extension=True)
    assert harness.cmd_setup(reg, args) == 1
    assert "install_extension" not in calls


# --------------------------------------------------------------------- blender
def test_blender_version_is_read_from_the_executable(monkeypatch):
    done = argparse.Namespace(stdout="Blender 4.2.0\n\tbuild date: 2024-07-16\n")
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: done)
    assert harness.blender_version("blender") == (4, 2, 0)


def test_a_flatpak_blender_keeps_its_config_under_var_app():
    path = harness.blender_config_dir((4, 2, 0), "/var/lib/flatpak/exports/bin/org.blender.Blender")
    assert path.as_posix().endswith(".var/app/org.blender.Blender/config/blender/4.2")


def test_blender_is_listed_once_per_real_file(tmp_path, monkeypatch):
    exe = tmp_path / ("blender.exe" if harness.os.name == "nt" else "blender")
    exe.write_text("")
    monkeypatch.setattr(harness.shutil, "which", lambda name: str(exe))
    found = harness.find_blender()
    assert found.count(str(exe)) == 1
