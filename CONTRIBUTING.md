# Contributing

Issues and pull requests are welcome. This page says what helps most, how to set
up a working copy, and what a change has to pass.

## What helps most

1. **A job report.** Run a job, then open a "Job report" issue with the prompt,
   the profile and workflow the harness chose, the render, and anything that
   failed. Reports from macOS and Linux matter most right now: the README's
   [Status](README.md#status) section lists what nobody has exercised yet.
2. **A lesson.** When a skill misbehaves in a real job and you found the fix, add
   an entry to [notes/lessons.md](notes/lessons.md). `resolve` prints the
   relevant entries at the end of every load plan, so the next job starts with
   them.
3. **Registry data.** Most changes to how the harness behaves are edits to YAML,
   not code (see the table below).
4. **The engine.** `scripts/harness.py` is one file with one dependency. Keep it
   that way.

## Set up a working copy

You need Git, [uv](https://docs.astral.sh/uv/getting-started/installation/) and,
for anything that touches Blender, Blender 4.2 or newer.

```bash
git clone https://github.com/MAX-786/claude-3d-harness.git
cd claude-3d-harness
uv run scripts/harness.py setup
```

On Windows, clone to a short path (for example `C:\dev\claude-3d-harness`), and
`.\scripts\install.ps1` does the same as the last line. Pass
`--skip-blender-extension` to leave Blender alone.

If you also have the plugin installed, disable it while you work in the clone.
Otherwise two Blender MCP servers compete for the same Blender.

## Before you open a pull request

```bash
uv run scripts/harness.py verify --strict
uv run --with pytest --with pyyaml pytest -q
```

CI runs both on Linux, macOS and Windows, and installs the pinned extension into
Blender 4.2 on Linux. If you changed `.claude-plugin/`, also run
`claude plugin validate .`.

## Where a change goes

| Task | Where |
| --- | --- |
| Prefer another skill for a capability | Swap `provider` and `fallbacks` in `registry/capabilities.yaml` |
| Handle a new upstream skill | Add it to `registry/skills.yaml` as `active`, `chained` or `excluded` |
| Add an upstream library | `git submodule add`, then an entry in `registry/upstreams.yaml` with its dialect, catalog and routes |
| Pin a newer MCP release | Update `release`, the URLs and both SHA-256 values in `registry/mcp.yaml`, then `harness.py mcp-config --write` |
| Change how much a profile spends | `registry/profiles.yaml` |
| Add or reorder stages of a job type | `workflows/<name>.yaml` |

## Rules `verify` enforces

- One provider per capability, or per variant. Alternatives go in `fallbacks`.
- One MCP server, named `blender`. `.mcp.json` is generated from
  `registry/mcp.yaml`; do not edit it by hand.
- Every SKILL.md an upstream ships is cataloged.
- The entry skill stays at the root as `SKILL.md`, with no root `skills/` folder.
  That layout gives the plugin its `/claude-3d-harness` command.

And two that a tool cannot check for you:

- **`upstream/` is read-only.** A fix to a skill's content belongs in that
  skill's own repository. What you learned goes to `notes/lessons.md`.
- **Never copy from `upstream/blender-skills`.** It has no license, so its author
  keeps all rights. Describe its skills in your own words
  ([THIRD_PARTY.md](THIRD_PARTY.md)).

## Writing a lesson

One bullet per lesson under a heading for the job. Start it with the skill id
and a short title in bold, then say what went wrong and what fixed it:

```markdown
## 2026-09-18 — job 20260918-2152-anime-rooftop-study (cinematic, Blender 5.2.2, newo-ether v1.18.0)

- **cc/blender-lighting — lights inside bulb meshes.** A light placed inside an emissive bulb mesh is
  blocked by it; set the bulb's `visible_shadow = False`.
- **Orientation checks in dim scenes.** A lesson that concerns no single skill leaves the id out.
```

`resolve` reads the bold part, so keep that form. `verify` warns when the id is
not in the catalog.

## Moving an upstream forward

Upstream skills are instructions Claude follows with code-execution rights
inside Blender, so nothing updates by itself. A weekly workflow runs
`harness.py outdated` and keeps one issue listing the pins that are behind.

```bash
uv run scripts/harness.py outdated          # read-only: which pins are behind?
uv run scripts/harness.py update cc         # move one upstream to its branch tip and audit the diff
uv run scripts/harness.py catalog-bump cc   # after reading the compare link: accept the new commit
git add registry upstream/cc-blender-skill
uv run scripts/harness.py update --rollback # or return to the pinned commits
```

Read the compare link and the audit output before `catalog-bump`. The audit
flags are prompts for a person, not verdicts.

## Releases

Installed plugins only update when `version` in `.claude-plugin/plugin.json`
changes. A release is: bump that version, move the "Unreleased" notes in
[CHANGELOG.md](CHANGELOG.md) under it, tag `v<version>`, publish a GitHub
release with those notes.
