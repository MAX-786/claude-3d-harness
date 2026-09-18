# claude-3d-harness

An orchestration layer over open-source Blender skill libraries. The 3D skills
live in git submodules under `upstream/`; this repository owns only the registry
that routes between them, the workflows, the complexity profiles and the install
and update tooling. Blender is driven through one MCP server named `blender`.

## When the user asks for anything 3D

Invoke the `blender-harness` skill before doing anything else, including for
requests that never mention Blender ("make a product shot of a watch"). It
classifies the job, picks a workflow and gets a load plan from the registry:

```bash
uv run scripts/harness.py resolve -w <workflow> -p <fast|standard|cinematic>
```

Read only the upstream files the load plan names. Do not pick skills by browsing
`upstream/`: the libraries overlap, use different MCP tool names, and some of
their skills must not run here. The registry already made those decisions.

## When maintaining the harness

| Path | What it holds |
| --- | --- |
| `registry/upstreams.yaml` | The submodules: repo, license, MCP dialect, `cataloged_at` commit |
| `registry/skills.yaml` | Every upstream SKILL.md, as `active`, `chained` or `excluded` |
| `registry/capabilities.yaml` | Capability to provider routing, with fallbacks and variants |
| `registry/profiles.yaml` | `fast`, `standard`, `cinematic`: always-on capabilities and budgets |
| `registry/mcp.yaml` | The MCP providers, the pinned release, the dialect translation tables |
| `workflows/*.yaml` | Ordered stages per job type |
| `orchestrator/*.md` | Classifier, workflow and skill selection rules, QA loop |
| `scripts/harness.py` | The engine: doctor, bootstrap, verify, resolve, update, audit |

Invariants, all enforced by `uv run scripts/harness.py verify`:

- One provider per capability (or per variant). Alternatives go in `fallbacks`.
- One MCP server, named `blender`. `.mcp.json` is generated from
  `registry/mcp.yaml` (`harness.py mcp-config --write`); do not edit it by hand.
- Every SKILL.md an upstream ships is cataloged. Uncataloged files are drift.
- `upstream/` is read-only. Changes to a skill go to its upstream repository;
  local lessons go to `notes/lessons.md`.

Run `verify` after any edit to `registry/` or `workflows/`. To move an upstream
forward: `uv run scripts/harness.py update <key>`, review the compare link and
the audit output, reconcile `registry/skills.yaml`, then
`uv run scripts/harness.py catalog-bump <key>` and commit the submodule pointer
together with the registry.

`upstream/blender-skills` has no license: reference it, never copy from it.
