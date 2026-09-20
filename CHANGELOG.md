# Changelog

Installed plugins only update when `version` in `.claude-plugin/plugin.json`
changes, so every entry here is a version a user can be on.

## 0.2.0 — unreleased

### Added

- **Lessons reach the next job.** `resolve` ends every load plan with the entries
  of `notes/lessons.md` that concern its skills, by line number, and the entry
  skill reads them before the stage that uses the skill. Until now lessons were
  written down and never read again. `verify` warns about a lesson filed under
  an id the catalog does not know.
- **`setup`.** One command for the whole install on Windows, macOS and Linux:
  upstreams, `.mcp.json`, the Blender extension, `doctor`, `verify`.
  `--provider`, `--blender` and `--skip-blender-extension` match the switches of
  `install.ps1`, which now only calls it.
- **`outdated`.** A read-only check of the pins against what the upstreams
  publish now: branch tips for the skill libraries, the latest release for the
  MCP server. It exits 3 when a pin is behind and changes nothing.
- **`verify --strict`** treats warnings as failures, for CI.
- **`--version`**, and `doctor` now opens with the harness version, the install
  type, the OS and the Python version, which is what a bug report needs.
- Blender is found in more places: `~/Applications` and Steam on macOS; `/opt`,
  `/usr/local`, the home folder, Steam and flatpak on Linux. A flatpak Blender's
  extension folder is looked up under `~/.var/app`.
- CI on Linux, macOS and Windows: `setup`, `verify --strict`, a load plan, the
  tests. A second job installs the pinned extension into Blender 4.2.0 on Linux
  and checks that `doctor` sees it.
- A weekly workflow that runs `outdated` and keeps one issue listing the pins
  that are behind. It never moves a pin.
- Tests for the engine (`tests/`), confined so pytest never imports anything
  under `upstream/`.
- `CONTRIBUTING.md`, `SECURITY.md`, issue forms (bug, job report, propose a skill
  library) and a pull request template.

### Changed

- Hints printed by the engine name `harness.py setup` and `bootstrap` instead of
  `install.ps1`, which does not exist for macOS and Linux users.
- A failed download of the Blender extension prints one line and returns,
  instead of a traceback.
- `LICENSE` is the plain MIT text again, so GitHub recognises it. The sentence
  about the submodules' own licenses moved to `THIRD_PARTY.md`.

## 0.1.0 — 2026-09-19

First public version: the registry over five upstream skill libraries, six
workflows, three profiles, one Blender MCP server, the `/claude-3d-harness`
plugin, and the rooftop study as the first `cinematic` job.
