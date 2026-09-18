# claude-3d-harness

One entry point for Claude Code over several open-source Blender skill
libraries. The libraries stay upstream, pinned as git submodules. This
repository adds what none of them can provide alone: a registry that picks one
skill per capability, translates between the MCP servers they were written for,
scales the effort to the job, and keeps a single Blender MCP server running.

```text
             Claude Code
                  |
        CLAUDE.md + blender-harness skill        the only skill Claude Code sees
                  |
   classify (fast / standard / cinematic) -> choose workflow
                  |
        scripts/harness.py resolve               registry -> ordered load plan
                  |
      upstream/<repo>/.../SKILL.md               read on demand, stage by stage
                  |
        MCP server "blender"  ->  Blender        render, inspect, refine
```

## Quick start (Windows)

Prerequisites: [Git](https://git-scm.com/download/win),
[uv](https://docs.astral.sh/uv/getting-started/installation/), Blender 4.2 or
newer, Claude Code. Optional: `ffmpeg` (camera-move videos), `node`.

Clone to a **short path**. Git on Windows cannot create submodule directories
when the repository root is deeper than about 150 characters.

```powershell
git clone https://github.com/MAX-786/claude-3d-harness.git C:\dev\claude-3d-harness
cd C:\dev\claude-3d-harness
.\scripts\install.ps1
```

The installer checks out the submodules at their pinned commits, writes
`.mcp.json`, downloads the MCP provider's Blender extension from its pinned
GitHub release, verifies the SHA-256 recorded in `registry/mcp.yaml`, installs it
into Blender, and runs the checks. Then start Blender, open the **BlenderMCP**
tab in the 3D View sidebar (`N`), open Claude Code in this folder, approve the
`blender` MCP server when asked, and describe what you want:

> Create a photorealistic interior of a traditional Japanese room during heavy
> rain. The camera slowly moves toward the window. Use free online assets where
> they help, build the rest, render a preview, inspect it and refine until the
> composition and lighting hold together.

On macOS or Linux run the same steps through the engine directly:
`uv run scripts/harness.py bootstrap`, `mcp-config --write`, `install-extension`,
`doctor`, `verify`.

A ZIP download from GitHub does not contain submodules. `install.ps1` handles
that case too: it initialises git and adds each upstream at the commit recorded
in `registry/upstreams.yaml`.

## What is composed

| Key | Upstream | License | Role here |
| --- | --- | --- | --- |
| `cc` | [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) | MIT | Primary library, 30 skills: execution conventions, modeling, materials, lighting, cameras, rendering, animation, export, reference-locked reconstruction, refinement loop |
| `gaius` | [Gaius114/blender-claude-mcp](https://github.com/Gaius114/blender-claude-mcp) | MIT | Specialists the primary lacks: architecture, procedural, geometry nodes, sculpting, rigging, physics, spatial math, research (written in Italian) |
| `kb` | [kevinbadi/blender-skills](https://github.com/kevinbadi/blender-skills) | none | Product camera moves, Poly Haven studio helpers, photo-to-3D |
| `jo` | [jithinolickal/blender](https://github.com/jithinolickal/blender) | Apache-2.0 | Parametric design workflow |
| `newo` | [newo-ether/blender-mcp](https://github.com/newo-ether/blender-mcp) | MIT | The MCP server (pinned release v1.18.0) and its usage skill |

61 upstream SKILL.md files are cataloged: 45 routable, 13 reached through a
parent skill, 3 excluded (two duplicates, and one that needs its own Blender
bridge). `uv run scripts/harness.py list skills` prints them all. See
[THIRD_PARTY.md](THIRD_PARTY.md) for the licensing notes, in particular for the
unlicensed upstream.

## Why a registry and not a folder of skills

Installing all five libraries side by side does not work, for reasons found
while cataloging them:

- **They target three different MCP servers.** Most call
  `mcp__blender__execute_blender_code` (ahujasid/blender-mcp). One calls
  `mcp__Blender__render_viewport_to_path` and other tools of a different
  connector. `registry/mcp.yaml` keeps a dialect table per upstream and the load
  plan prints the translation next to the skill that needs it.
- **Names collide.** Two libraries ship `blender-lighting`; one ships duplicate
  copies of its own skills. Claude Code would see both. Here the registry
  namespaces them (`cc/blender-lighting`, `gaius/blender-lighting`), routes one
  and lists the other as a fallback.
- **Some skills bypass MCP.** Seven bundle node scripts that open the Blender
  addon socket themselves. They are marked `direct-socket`; under the default
  provider Claude takes their parameters and performs the steps through MCP.
- **Some skills must not run here**: one needs its own WebSocket addon, one
  rewrites skill files and cuts releases as part of its loop. The first is
  excluded, the second carries a note and `upstream/` is edit-denied in
  `.claude/settings.json`.
- **Context cost.** Several skills exceed a thousand lines. Only the entry skill
  is registered with Claude Code; everything else is read on demand, a stage at a
  time.

## Profiles and workflows

Profiles (`registry/profiles.yaml`) decide which stages run and how much
iteration a job may spend.

| Profile | For | Budget |
| --- | --- | --- |
| `fast` | One simple object or a small edit | Inline plan, one checkpoint, one fix pass, 720p |
| `standard` | Several objects, real materials and light, one deliverable | Plan file, three checkpoints, two fix passes, 1080p |
| `cinematic` | Environment, atmosphere, camera motion, film look | Full plan, gate per stage, four fix passes, contact sheet before any animation render |

Workflows (`workflows/*.yaml`): `modeling`, `product`, `photography`,
`animation`, `environment`, `cinematic`. Try the resolver without Blender:

```powershell
uv run scripts/harness.py resolve -w product -p standard --variant camera-animation=perfect-loop
uv run scripts/harness.py resolve -w cinematic -p cinematic --variant camera-animation=slow-zoom
uv run scripts/harness.py list capabilities
```

## The MCP layer

Exactly one server, always named `blender`, generated into `.mcp.json` from
`registry/mcp.yaml`.

| Provider | What | When |
| --- | --- | --- |
| `newo-ether` (default) | Fork of the original server that keeps its tool names and adds structured node editing, Blender documentation search and multi-instance claiming. Runs via `uvx` from the pinned v1.18.0 wheel. | Default. Blender 4.2+. |
| `ahujasid` | The original ([ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender), `blender-mcp==2.0.0`), which every skill library was validated against. | Fallback: `.\scripts\install.ps1 -Mcp ahujasid`, then install its `addon.py` by hand. |

Telemetry is switched off in the generated config (`DISABLE_TELEMETRY=true`);
remove that line in `registry/mcp.yaml` if you want to opt in. If you ever run
the fork's own installer as well, pass its `-SkipClaudeCodeRegistration`,
`-SkipCodexRegistration`, `-SkipClaudeDesktop` and `-SkipSkillInstallation`
switches, otherwise a second server named `blender_mcp` competes for the same
Blender. `doctor` warns about user-scope duplicates.

`.claude/settings.json` pre-allows the read-only MCP tools and the harness
script. `execute_blender_code` runs arbitrary Python inside Blender and is left
to prompt; choose "always allow" in Claude Code if you want unattended runs.

## Maintaining the pins

```powershell
.\scripts\update.ps1 -Only cc        # move one upstream to its branch tip
.\scripts\update.ps1                 # or all of them
.\scripts\update.ps1 -Rollback       # back to the pinned commits
```

`update` stages nothing. It prints a GitHub compare link per moved upstream,
reports drift (SKILL.md files added or removed upstream), and audits the changed
files for patterns worth a human look: network calls, shell execution,
credentials, agent-config tampering, installs, destructive file operations.
Upstream skills are instructions that Claude follows with code-execution rights
inside Blender, so read the diff before accepting it. Then:

```powershell
uv run scripts/harness.py catalog-bump cc
git add registry upstream/cc-blender-skill
git commit -m "Bump cc-blender-skill"
```

Other maintenance:

| Task | How |
| --- | --- |
| Prefer another provider for a capability | Swap `provider` and `fallbacks` in `registry/capabilities.yaml` |
| Handle a new upstream skill | Add it to `registry/skills.yaml` as `active`, `chained` or `excluded` |
| Add an upstream repository | `git submodule add`, entry in `registry/upstreams.yaml` with its dialect, catalog, route |
| Pin a newer MCP release | Update `release`, the URLs and both SHA-256 values in `registry/mcp.yaml`, run `harness.py mcp-config --write` |
| Check everything | `.\scripts\verify.ps1` |

## Layout

```text
.claude/skills/blender-harness/   the entry-point skill
.claude/settings.json             read-only MCP tools allowed, upstream/ edit-denied
.mcp.json                         generated: one server named "blender"
CLAUDE.md                         always-on contract for Claude
registry/                         upstreams, skills, capabilities, profiles, mcp
workflows/                        six job types as ordered stages
orchestrator/                     classifier, selectors, QA loop
scripts/                          harness.py engine + install / update / verify wrappers
upstream/                         the submodules (read-only)
notes/lessons.md                  local lessons that would otherwise go into upstream files
output/                           job folders: plans, previews, renders (git-ignored)
```

## Status

Verified: the registry resolves against the real upstream trees at the pinned
commits (`verify` reports 0 failures and 0 warnings), every documented `resolve`
command runs, provider switching and fallbacks behave as described.

Not yet exercised: a live Blender session through the harness, the extension
installer, and the ZIP-download bootstrap path. The machine this was assembled
on had no Blender installed.

## License

The harness itself is MIT ([LICENSE](LICENSE)). Each submodule keeps its own
license; see [THIRD_PARTY.md](THIRD_PARTY.md).
