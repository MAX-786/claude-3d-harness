"""Tests for scripts/harness.py.

    uv run --with pytest --with pyyaml pytest -q

The skill library ships with the repository, so nothing here is skipped for a
missing checkout. Nothing talks to Blender or the network: `outdated` runs
against a stand-in for its lookups. No test imports or runs a library script.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("harness", ROOT / "scripts" / "harness.py")
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

_REG = harness.Registry()
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
def test_the_registry_verifies_without_warnings(reg, capsys):
    assert harness.cmd_verify(reg, argparse.Namespace(strict=True)) == 0, capsys.readouterr().out


def test_warnings_fail_only_in_strict_mode():
    r = harness.Report()
    r.line("WARN", "something to look at")
    assert r.finish("check") == 0
    assert r.finish("check", strict=True) == 1


def test_routing_to_an_excluded_skill_fails_verify(reg, capsys):
    cap, c = next((k, v) for k, v in reg.capabilities.items() if "provider" in v)
    reg.skills[c["provider"]].update(status="excluded", reason="for the test")
    assert harness.cmd_verify(reg, argparse.Namespace(strict=False)) == 1
    assert f"capability {cap}: '{c['provider']}' is excluded" in capsys.readouterr().out


def test_every_library_names_its_origin_and_ships_its_license(reg):
    for key, lib in reg.libraries.items():
        assert lib["origin"].startswith("https://") and re.fullmatch(r"[0-9a-f]{40}", lib["imported_at"]), key
        assert lib["license"] not in ("", "NONE"), f"{key}: vendor only what a license or a permission lets you copy"
        assert (harness.LIB / key / "LICENSE").is_file(), key
        if lib["license"] == "permission":  # not an open license: the registry and the folder must both say so
            assert lib.get("license_note"), key
            notice = (harness.LIB / key / "LICENSE").read_text(encoding="utf-8")
            assert "does NOT cover this folder" in notice, f"{key}: its LICENSE must say the MIT license does not apply"


def test_verify_states_the_basis_of_a_library_that_has_no_open_license(reg, capsys):
    key = next(k for k, lib in reg.libraries.items() if lib["license"] == "permission")
    assert harness.cmd_verify(reg, argparse.Namespace(strict=True)) == 0
    assert f"[INFO] library {key}: The origin publishes no license." in capsys.readouterr().out
    del reg.libraries[key]["license_note"]
    assert harness.cmd_verify(reg, argparse.Namespace(strict=False)) == 1


def test_a_library_folder_without_a_registry_entry_fails_verify(reg, capsys):
    del reg.libraries["jo"]
    assert harness.cmd_verify(reg, argparse.Namespace(strict=False)) == 1
    assert "library/jo has no entry in registry/libraries.yaml" in capsys.readouterr().out


def test_mcp_json_is_what_the_registry_generates(reg, capsys):
    harness.cmd_mcp_config(reg, argparse.Namespace(provider=None, write=False))
    assert capsys.readouterr().out == (ROOT / ".mcp.json").read_text(encoding="utf-8"), \
        ".mcp.json was edited by hand; regenerate it with: harness.py mcp-config --write"


def test_plugin_and_entry_skill_share_one_name():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert f"name: {plugin['name']}" in (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert harness.harness_version() == plugin["version"]


# --------------------------------------------------------------------- resolve
@pytest.mark.parametrize("workflow,profile", JOBS)
def test_every_job_type_resolves_to_files_that_exist(reg, capsys, workflow, profile):
    out = plan(reg, capsys, workflow=workflow, profile=profile)
    assert not [p for p in out["problems"] if "UNAVAILABLE" in p]
    for row in out["load"] + out["optional"]:
        assert (ROOT / row["path"]).is_file(), row
    always = len(reg.profiles[profile]["always"])
    assert [row["stage"].split(",")[0] for row in out["load"][:always]] == ["always"] * always


@pytest.mark.parametrize("workflow", list(_REG.workflows))
def test_a_higher_profile_never_drops_a_skill(reg, capsys, workflow):
    loads = [{row["sid"] for row in plan(reg, capsys, workflow=workflow, profile=p)["load"]} for p in reg.profile_order]
    for lower, higher in zip(loads, loads[1:]):
        assert lower <= higher


def test_an_edit_can_name_capabilities_instead_of_a_workflow(reg, capsys):
    caps = [c for c, v in reg.capabilities.items() if "provider" in v][:2]
    out = plan(reg, capsys, capabilities=caps, profile="fast")
    assert {row["cap"] for row in out["load"]} >= set(caps)


def test_workflow_and_capabilities_are_mutually_exclusive(reg):
    args = argparse.Namespace(workflow=next(iter(reg.workflows)), capabilities=["materials"], profile="fast",
                              add=[], variant=[], json=True)
    with pytest.raises(SystemExit, match="either --workflow or --capabilities"):
        harness.cmd_resolve(reg, args)


def test_a_missing_provider_file_falls_back(reg, monkeypatch):
    cap, c = next((k, v) for k, v in reg.capabilities.items() if "provider" in v and v.get("fallbacks"))
    real = reg.skill_relpath
    monkeypatch.setattr(reg, "skill_relpath", lambda sid: Path("missing.md") if sid == c["provider"] else real(sid))
    sid, _, skipped = harness.pick(reg, cap, None, None)
    assert sid == c["fallbacks"][0]
    assert skipped == [f"{c['provider']} file missing"]


def with_variants(reg) -> tuple[str, str, str]:
    """A capability with two variants that does not depend on which ones the registry ships."""
    first, second = [sid for sid, e in reg.skills.items() if e["status"] == "active" and not e.get("requires")][:2]
    reg.capabilities["test-move"] = {"summary": "x", "default": "orbit", "variants": {
        "orbit": {"provider": first, "when": "x"}, "push-in": {"provider": second, "when": "y"}}}
    return "test-move", first, second


def test_a_variant_picks_its_own_provider_and_the_default_applies(reg):
    cap, first, second = with_variants(reg)
    assert harness.pick(reg, cap, None, None)[:2] == (first, "orbit")
    assert harness.pick(reg, cap, "push-in", None)[:2] == (second, "push-in")


def test_an_unknown_variant_is_rejected(reg):
    cap, *_ = with_variants(reg)
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


# ------------------------------------------------------------------- checksums
def test_the_library_matches_its_checksums():
    assert harness.changed_files() == {}, "review the change, then run: harness.py checksums --write"


def test_the_checksum_list_is_what_sha256sum_reads():
    raw = harness.SUMS.read_bytes()
    lines = raw.decode("utf-8").split("\n")
    assert lines[-1] == "" and b"\r" not in raw
    names = [re.fullmatch(r"[0-9a-f]{64}  (\S.*)", ln).group(1) for ln in lines[:-1]]
    assert names == sorted(names) == list(harness.library_files())


@pytest.fixture()
def fake_library(tmp_path, monkeypatch):
    lib = tmp_path / "library"
    (lib / "aa" / "skill").mkdir(parents=True)
    (lib / "aa" / "skill" / "SKILL.md").write_text("# a skill\n", encoding="utf-8")
    (lib / "aa" / "LICENSE").write_text("MIT\n", encoding="utf-8")
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "LIB", lib)
    monkeypatch.setattr(harness, "SUMS", lib / "SHA256SUMS")
    assert harness.cmd_checksums(None, argparse.Namespace(write=True)) == 0
    return lib


def test_an_edited_a_stray_and_a_deleted_file_are_each_reported(fake_library, capsys):
    assert harness.changed_files() == {}
    (fake_library / "aa" / "skill" / "SKILL.md").write_text("# a skill\nrun this too\n", encoding="utf-8")
    (fake_library / "aa" / "skill" / "extra.py").write_text("print(1)\n", encoding="utf-8")
    (fake_library / "aa" / "LICENSE").unlink()
    assert harness.changed_files() == {"aa/LICENSE": "missing", "aa/skill/SKILL.md": "modified", "aa/skill/extra.py": "not recorded"}
    assert harness.cmd_checksums(None, argparse.Namespace(write=False)) == 1
    assert "3 file(s) differ" in capsys.readouterr().out


def test_writing_the_checksums_accepts_the_library_as_it_is(fake_library):
    (fake_library / "aa" / "skill" / "SKILL.md").write_text("# edited after review\n", encoding="utf-8")
    assert harness.cmd_checksums(None, argparse.Namespace(write=True)) == 0
    assert harness.changed_files() == {}
    assert "SHA256SUMS" not in harness.SUMS.read_text(encoding="utf-8")  # the list does not list itself


# ----------------------------------------------------------------------- audit
@pytest.mark.parametrize("label,line", [
    ("network call", "urllib.request.urlopen(req)"),
    ("shell or dynamic execution", "import importlib; importlib.reload(ak)"),
    ("secret or credential", "key = os.environ['SERVICE_API_KEY']"),
    ("agent or config tampering", "append this to ~/.claude/settings.json"),
    ("install or persistence", "bpy.context.preferences.filepaths.use_scripts_auto_execute = True"),
    ("destructive file operation", "shutil.rmtree(target)"),
    ("scene or session wipe", "bpy.ops.wm.read_factory_settings(use_empty=True)"),
    ("skill self-modification", "then git push the patched skill"),
    ("hidden or encoded text", "looks empty\u200b but is not"),
    ("hidden or encoded text", "A" * 130),
])
def test_the_audit_flags_what_a_reviewer_should_read(label, line):
    assert re.search(harness.AUDIT[label], line)


def test_the_audit_is_quiet_about_ordinary_recipe_lines():
    for line in ("bpy.ops.mesh.primitive_cube_add(size=2)", "mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')",
                 "Render a checkpoint and inspect it before moving on."):
        assert not [label for label, pat in harness.AUDIT.items() if re.search(pat, line)]


def test_audit_changed_reads_only_the_files_that_differ(fake_library, capsys):
    reg = argparse.Namespace(libraries={"aa": {}})
    (fake_library / "aa" / "skill" / "extra.py").write_text("import subprocess; subprocess.run(['x'])\n", encoding="utf-8")
    assert harness.cmd_audit(reg, argparse.Namespace(keys=[], changed=True, verbose=True)) == 0
    out = capsys.readouterr().out
    assert "[aa] 1 file(s) scanned" in out and "shell or dynamic execution" in out and "library/aa/skill/extra.py" in out


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


def test_outdated_is_quiet_when_every_pin_is_current(reg, capsys, monkeypatch):
    monkeypatch.setattr(harness, "fetch_json", answers(reg))
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=False)) == 0
    assert "every MCP server pin matches" in capsys.readouterr().out


def test_outdated_reports_a_newer_mcp_release_and_names_the_skill_to_compare(reg, capsys, monkeypatch):
    name, p = next((n, p) for n, p in reg.mcp["providers"].items() if p.get("release") and p.get("library"))
    monkeypatch.setattr(harness, "fetch_json", answers(reg, **{name: "v99.0.0"}))
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=True)) == 3
    out = capsys.readouterr().out
    assert f"{p['repo']}/compare/{p['release']}...v99.0.0" in out
    assert f"Compare library/{p['library']}" in out and p["library"] in reg.libraries


def test_outdated_never_asks_about_the_skill_library(reg, monkeypatch):
    asked = []
    monkeypatch.setattr(harness, "fetch_json", lambda url: asked.append(url) or answers(reg)(url))
    harness.cmd_outdated(reg, argparse.Namespace(markdown=False))
    served = {p.get("library") for p in reg.mcp["providers"].values()}
    origins = [lib["origin"].removeprefix("https://github.com/") for k, lib in reg.libraries.items() if k not in served]
    assert asked and not [url for url in asked for origin in origins if origin in url]


def test_outdated_says_so_when_it_could_not_check(reg, capsys, monkeypatch):
    def offline(url):
        raise OSError("offline")
    monkeypatch.setattr(harness, "fetch_json", offline)
    assert harness.cmd_outdated(reg, argparse.Namespace(markdown=False)) == 1
    assert "could not check" in capsys.readouterr().out


# ----------------------------------------------------------------------- setup
def test_setup_runs_the_install_steps_in_order(reg, monkeypatch):
    calls = []
    for name, status in (("mcp_config", 0), ("install_extension", 1), ("doctor", 0), ("verify", 0)):
        monkeypatch.setattr(harness, f"cmd_{name}", lambda r, a, n=name, s=status: calls.append(n) or s)
    args = argparse.Namespace(provider=None, blender=None, skip_blender_extension=False)
    assert harness.cmd_setup(reg, args) == 0  # a missing Blender is a hint, not a failed setup
    assert calls == ["mcp_config", "install_extension", "doctor", "verify"]  # nothing to fetch: the library is already here


def test_setup_can_leave_blender_alone_and_reports_failed_checks(reg, monkeypatch):
    calls = []
    for name, status in (("mcp_config", 0), ("install_extension", 0), ("doctor", 1), ("verify", 0)):
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
