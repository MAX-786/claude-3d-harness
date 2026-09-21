# claude-3d-harness

A harness for building 3D scenes in Blender with Claude Code. The 3D skills
live in `library/`: five skill libraries, vendored, security-reviewed and
checksummed. Four ship an open license at their origin; `library/kb`'s origin
has none, so its MIT grant was given directly to the maintainer. Around them
sit the registry that routes between them, the workflows, the complexity
profiles and the install tooling. Blender is driven through one MCP server
named `blender`.

## When the user asks for anything 3D

Invoke the `blender-harness` skill before doing anything else, including for
requests that never mention Blender ("make a product shot of a watch"). It points
to the entry skill, `SKILL.md` at the repository root, which classifies the job,
picks a workflow and gets a load plan from the registry:

```bash
uv run scripts/harness.py resolve -w <workflow> -p <fast|standard|cinematic>
```

Read only the library files the load plan names. Do not pick skills by browsing
`library/`: the libraries overlap and use different MCP tool names. The registry
already made those decisions.

## When maintaining the harness

| Path | What it holds |
| --- | --- |
| `library/<key>/` | The skills, one folder per library, each with its `LICENSE`. `library/SHA256SUMS` records every file as reviewed |
| `registry/libraries.yaml` | The libraries: origin, imported commit, license, MCP dialect, what was omitted or changed |
| `registry/skills.yaml` | Every SKILL.md in `library/`, as `active`, `chained` or `excluded` |
| `registry/capabilities.yaml` | Capability to provider routing, with fallbacks and variants |
| `registry/profiles.yaml` | `fast`, `standard`, `cinematic`: always-on capabilities and budgets |
| `registry/mcp.yaml` | The MCP providers, the pinned release, the dialect translation tables |
| `workflows/*.yaml` | Ordered stages per job type |
| `orchestrator/*.md` | Classifier, workflow and skill selection rules, QA loop |
| `scripts/harness.py` | The engine: setup, doctor, verify, resolve, outdated, audit, checksums |
| `tests/` | Tests for the engine. `pytest.ini` keeps pytest out of `library/`, where collecting a file would run it |
| `.github/workflows/` | `ci.yml` (three OSes, plus the extension install into Blender 4.2 on Linux) and the weekly `mcp-watch.yml` |
| `docs/security-review.md` | What the library was reviewed for, what was found, what was changed. Add to it when a library or a risky change comes in |
| `notes/lessons.md` | Lessons from real jobs. `resolve` prints the ones that concern a load plan's skills, so keep the entry form the file describes |
| `SKILL.md` | The entry skill. Installed as a plugin, it is the `/claude-3d-harness` command |
| `.claude-plugin/` | Plugin and marketplace manifests; bump `version` in `plugin.json` to release, and move the "Unreleased" notes in `CHANGELOG.md` |

Invariants, all enforced by `uv run scripts/harness.py verify`:

- One provider per capability (or per variant). Alternatives go in `fallbacks`.
- One MCP server, named `blender`. `.mcp.json` is generated from
  `registry/mcp.yaml` (`harness.py mcp-config --write`); do not edit it by hand.
- Every SKILL.md in `library/` is cataloged. Uncataloged files are drift.
- Every file in `library/` matches `library/SHA256SUMS`. After editing a skill:
  `uv run scripts/harness.py audit --changed`, read what it flags, then
  `uv run scripts/harness.py checksums --write`, and commit both together.
- Every library has an entry in `registry/libraries.yaml` and ships its
  `LICENSE`. Only vendor what a license or a permission lets you copy; a library
  with `license: permission` needs a `license_note`, which `verify` prints.
- `library/` is never edited during a 3D job; lessons go to `notes/lessons.md`.
  Improving a skill is a separate change, reviewed like code, because Claude
  follows these files with code-execution rights inside Blender.
- The entry skill stays at the root as `SKILL.md`, and there is no root
  `skills/` directory. That layout makes the plugin's command
  `/claude-3d-harness`; the plugin, marketplace and skill names must match.
  The plugin reuses the root `.mcp.json`.

Run `verify` after any edit to `library/`, `registry/`, `workflows/`, `SKILL.md`
or `.claude-plugin/`, and `claude plugin validate .` after editing the manifests.
After editing `scripts/harness.py`, run the tests:
`uv run --with pytest --with pyyaml pytest -q`. CI runs `verify --strict` and
the tests on Linux, macOS and Windows. The library follows nobody's
branch: to take an improvement from a library's origin, port it by hand as a
skill change (never re-import a folder, which would undo the security fixes).

`library/kb`'s origin ships no LICENSE file. It is vendored MIT on the author's
statement, given directly to the maintainer, that the work is MIT licensed
(`library/kb/LICENSE` carries that text under the author's name). Do not copy
anything else from that origin (its `blender-toolkit/` is another author's
work), and never copy from any source without a published license or a clear
grant that allows it.
