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

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and, for
anything that touches Blender, Blender 4.2 or newer. Git is only needed to clone.

```bash
git clone https://github.com/MAX-786/claude-3d-harness.git
cd claude-3d-harness
uv run scripts/harness.py setup
```

On Windows, `.\scripts\install.ps1` does the same as the last line. Pass
`--skip-blender-extension` to leave Blender alone. Nothing else is fetched: the
skill library is part of the repository.

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
| Fix or improve a skill | Edit it under `library/`, then follow "Changing a skill" below |
| Catalog a new skill | Add it to `registry/skills.yaml` as `active`, `chained` or `excluded` |
| Add a library | "Adding a library" below |
| Pin a newer MCP release | Update `release`, the URLs and both SHA-256 values in `registry/mcp.yaml`, then `harness.py mcp-config --write` |
| Change how much a profile spends | `registry/profiles.yaml` |
| Add or reorder stages of a job type | `workflows/<name>.yaml` |

## Rules `verify` enforces

- One provider per capability, or per variant. Alternatives go in `fallbacks`.
- One MCP server, named `blender`. `.mcp.json` is generated from
  `registry/mcp.yaml`; do not edit it by hand.
- Every SKILL.md in `library/` is cataloged.
- Every file in `library/` matches `library/SHA256SUMS`, every library has an
  entry in `registry/libraries.yaml`, and every library ships its `LICENSE`.
- The entry skill stays at the root as `SKILL.md`, with no root `skills/` folder.
  That layout gives the plugin its `/claude-3d-harness` command.

And two that a tool cannot check for you:

- **Only copy what a license or a permission lets you copy.** A public
  repository without a license is not open source: its author keeps all rights.
  `library/kb` is such a case, included by permission and labelled so
  ([THIRD_PARTY.md](THIRD_PARTY.md)). A pull request that adds files without an
  open license needs the permission in writing, in the pull request.
- **A skill change is a code change.** Claude follows these files with
  code-execution rights inside Blender, so read a skill diff the way you would
  read a diff to a script that runs on your users' machines.

## Changing a skill

```bash
# edit the file under library/, then:
uv run scripts/harness.py audit --changed   # flags the lines a reviewer should read
uv run scripts/harness.py checksums --write # record the library as reviewed
uv run scripts/harness.py verify --strict
```

Commit the skill and `library/SHA256SUMS` together. `verify` fails when they
disagree, so nobody can change a skill without the list changing in the same
pull request. Keep the change free of the things
[docs/security-review.md](docs/security-review.md) removed: paths on your own
machine, package installs, network helpers, steps that clear or save the user's
scene, instructions to edit skill files. If you change a file of `library/jo`,
Apache-2.0 asks for a notice in that file saying it was changed.

## Adding a library

1. Check the license. MIT, Apache-2.0, BSD, CC0 and the like allow copying. No
   license means no, unless the author gives permission in writing: then the
   entry is `license: permission` with a `license_note`, and the folder's
   `LICENSE` says that the MIT license does not cover it.
2. Import only the skill folders, from a named commit, plus the `LICENSE` file as
   `library/<key>/LICENSE`. Leave out installers, add-ons, bridges and servers:
   the harness runs one MCP server and nothing else.
3. Review every file against the list in
   [docs/security-review.md](docs/security-review.md), and add what you found and
   changed to that document.
4. Add the entry to `registry/libraries.yaml` (origin, commit, license, dialect,
   language, what was omitted), catalog the skills in `registry/skills.yaml`, and
   route the ones that fill a gap in `registry/capabilities.yaml`.
5. `uv run scripts/harness.py checksums --write`, then `verify --strict`.

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

## Taking an improvement from a library's origin

The library follows nobody's branch. `uv run scripts/harness.py list libraries`
prints each origin and the commit it was imported from, so
`<origin>/compare/<commit>...main` shows what its author has done since. Port
what is worth having by hand, as a skill change like any other. Do not re-import
a folder wholesale: that would undo the security fixes.

## Moving the MCP server forward

The server and its Blender extension are the one thing still fetched at install
time, from a pinned release. A weekly workflow runs `harness.py outdated` and
keeps one issue open while the pin is behind. To move it: update `release`,
both URLs and both SHA-256 values in `registry/mcp.yaml`, run
`harness.py mcp-config --write`, and compare `library/newo` with the skill the
new release ships.

## Releases

Installed plugins only update when `version` in `.claude-plugin/plugin.json`
changes. A release is: bump that version, move the "Unreleased" notes in
[CHANGELOG.md](CHANGELOG.md) under it, tag `v<version>`, publish a GitHub
release with those notes.
