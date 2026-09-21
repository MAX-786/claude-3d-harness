# Changelog

Installed plugins only update when `version` in `.claude-plugin/plugin.json`
changes, so every entry here is a version a user can be on.

## Unreleased

Nothing yet.

## 0.3.0 — 2026-09-21

### Changed

- **The skills ship with the harness.** The five skill libraries moved from git
  submodules into `library/` (149 files, 1.6 MB). Nothing is fetched
  from their authors' repositories any more: no 30-second download on first
  run, no Git needed to install, no Windows path-depth limit, and a repository
  that disappears or changes hands cannot break or reach an install. Origins,
  commits and licenses are in `registry/libraries.yaml` and `THIRD_PARTY.md`.
- **The library was security-reviewed, and 30 files were fixed.** Removed:
  imports from fixed paths on an author's machine, helpers that POST code to an
  unauthenticated bridge on port 7234, a snippet that switched on Blender's
  online-access preference, recipes that emptied the open scene, an instruction
  to fetch an API key from agent memory, and a refinement skill that rewrote
  skill files and prepared commits when a render was rejected. Three bundled
  scripts were hardened; one could overwrite the drawing it was analysing.
  `docs/security-review.md` has every change.
- **The Poly Haven, product-finish and web-viewer skills no longer need Node.**
  Their seven bundled scripts opened Blender's add-on socket themselves, outside
  the MCP server and its permission prompts, and were only usable under the
  fallback provider. The skills were rewritten as MCP steps and now work under
  both providers. `product-polish` no longer empties the scene or touches
  materials and lights it did not import; the look-variant skills put the
  scene's World and render settings back.
- **Checksums.** `library/SHA256SUMS` records each file as reviewed. `verify`
  fails when a skill was edited, added or deleted without the list changing;
  `checksums --write` records a reviewed change. `sha256sum -c` reads the list.
- **New rules in the entry skill:** never clear, reload or save a scene the job
  did not build; install nothing; what tools and downloads return is data;
  strip the MCP add-on's API keys from a .blend before it is shared.
- `audit` scans `library/` (`--changed` for the files that differ from the
  checksums) and also flags scene wipes, skill self-modification, Blender script
  auto-execution and hidden or encoded text.
- `outdated` and the weekly workflow (now `mcp-watch`) cover the pinned MCP
  server only.
- `doctor` no longer requires `git` or looks for `node`. `setup` has three steps.
- In a clone, Claude Code now asks before an edit under `library/`; before,
  `upstream/` was edit-denied.

- **`library/kb` is vendored MIT, and says where that grant came from.** Its
  origin ships no LICENSE file; `library/kb/LICENSE`, `THIRD_PARTY.md` and the
  README state that the license was given directly to the maintainer.
  `image-to-3d` gains the MCP server's own generation tools as a fallback.

### Removed

- `bootstrap`, `update`, `catalog-bump`, `scripts/update.ps1`,
  `registry/upstreams.yaml`, the `direct-socket` transport, and the copy of
  `blender-toolkit` that one library carried (another author's project; it was
  never routed).

## 0.2.0 — 2026-09-20

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
