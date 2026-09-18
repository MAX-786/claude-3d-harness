---
name: claude-3d-harness
description: Entry point for every 3D or Blender task - modeling, materials, lighting, cameras, rendering, animation, product shots, environments, cinematic scenes, exports. Classifies the job (fast, standard or cinematic), picks a workflow, asks the harness registry which upstream skills to load, then drives Blender through the harness's single Blender MCP server with render, inspect and refine checkpoints. Use it whenever the user asks to create, change, light, render, animate or export anything in 3D, even if they never say "Blender".
argument-hint: <what to build in Blender>
---

# claude-3d-harness

The user's request: $ARGUMENTS

If the request is empty, ask what they want to build before doing anything else.

This harness contains no 3D skills of its own. It composes five upstream skill
libraries, pinned as git submodules under `upstream/`, behind one registry. The
upstreams overlap (two ship a `blender-lighting`), were written for three
different MCP servers, and one is in Italian. The registry settles all of that:
one provider per capability, one MCP server, and a note for every adaptation you
need to make. So never browse `upstream/` to choose skills yourself. Ask the
registry, then read exactly what it names.

## Where things are

- **Harness root.** Written `H` below. It is `${CLAUDE_PLUGIN_ROOT}`, which
  Claude Code fills in when the harness is installed as a plugin. If you see
  that placeholder literally instead of a path, you are working in a clone of
  the repository, and `H` is the repository root: the folder that holds this
  file and `registry/`.
- **Engine.** `uv run "H/scripts/harness.py" <command>` works from any directory.
  Paths in its output are relative to `H`, which it prints on the first line.
- **Job folders.** `output/<yyyymmdd-hhmm>-<slug>/` inside the user's project
  (`${CLAUDE_PROJECT_DIR}`, or the current directory in a clone), never inside
  `H`. The Blender MCP server uses the same `output/` folder as its workspace.
- **Tool names.** The harness runs one Blender MCP server, named `blender`.
  Installed as a plugin, its tools appear as
  `mcp__plugin_claude-3d-harness_blender__<tool>`; in a clone they appear as
  `mcp__blender__<tool>`. The registry, the load plan and the upstream skills
  always write `mcp__blender__<tool>`: call the same `<tool>` on whichever of
  the two servers exists.

## Procedure

### 0. First run and preflight

Run `uv run "H/scripts/harness.py" doctor` before the first Blender call of the
session and act on what it reports:

| doctor reports | Do this |
| --- | --- |
| `uv` not found (the command itself fails) | Stop. Ask the user to install uv: https://docs.astral.sh/uv/getting-started/installation/ |
| `git: not found` | Stop. Ask the user to install Git; fetching the upstream libraries needs it. |
| `submodules checked out: missing ...` | Run `uv run "H/scripts/harness.py" bootstrap`, then `verify`. It downloads the five upstream libraries at their pinned commits, about 30 seconds, once per installed version. Tell the user that is what is happening. |
| `Blender (>= 4.2 needed): not found` | Ask for the path to the Blender executable and pass it as `--blender <path>` below. |
| `extension 'blender_mcp': NOT installed` | Ask first, then run `uv run "H/scripts/harness.py" install-extension`. It downloads the pinned Blender extension, checks its SHA-256 and installs it into every Blender 4.2+ it finds. Blender needs a restart afterwards. |

Then check that Blender answers: call `list_blender_instances`. If no instance
is listed, ask the user to start Blender, press `N` in the 3D View and open the
**BlenderMCP** tab, then call it again. If the Blender MCP tools are missing
altogether, the server did not start: ask the user to restart Claude Code and,
if that does not help, to check `/mcp`. Do not switch to GUI automation or any
other bridge: a second execution path is exactly what this harness exists to
prevent. Look at what is already in the scene before changing anything.

### 1. Classify the job into a profile

| Profile | The request looks like | Spend |
| --- | --- | --- |
| `fast` | One simple object, or a small edit to a scene that already exists | Inline plan, one checkpoint, one fix pass |
| `standard` | Several objects, believable materials and lighting, a composed camera, one deliverable | Plan file, three checkpoints, two fix passes |
| `cinematic` | A full environment or film-quality shot: many asset types, atmosphere, camera motion, "photorealistic" | Full plan, a gate after every stage, four fix passes |

When two profiles fit, take the lower one and say so in one line; the user can
ask for more. An explicit request ("keep it quick", "go all out") always wins.
Edge cases and worked examples: `H/orchestrator/task-classifier.md`.

### 2. Choose one workflow

| Workflow | Use when |
| --- | --- |
| `modeling` | The object itself is the deliverable (asset, prop, part) |
| `product` | One product presented for sale: packshot, hero still, optional spin |
| `photography` | The request is phrased photographically, or an existing scene needs to be shot well |
| `animation` | Motion is the deliverable: object animation, camera move, loop |
| `environment` | A place with many objects, delivered as a still |
| `cinematic` | Environment plus atmosphere plus a graded final frame, usually with camera motion |

For an edit to an existing scene, skip the workflow and name capabilities
directly (`-c materials lighting`). Combining and tie-breaks:
`H/orchestrator/workflow-selector.md`.

### 3. Get the load plan

```bash
uv run "H/scripts/harness.py" resolve -w <workflow> -p <profile>
uv run "H/scripts/harness.py" resolve -w product -p standard --variant camera-animation=perfect-loop
uv run "H/scripts/harness.py" resolve -w modeling -p fast --add architecture
uv run "H/scripts/harness.py" resolve -c materials lighting -p fast
```

The plan lists, in order, the SKILL.md files to read, the optional stages with
their conditions, alternatives you can add, the budgets of the profile, and the
adaptation notes for the skills it chose. `uv run "H/scripts/harness.py" list
capabilities` shows the whole vocabulary. Read the skills marked `always` now.

### 4. Plan

Follow the `plan` budget. For `standard` and `cinematic`, create
`output/<yyyymmdd-hhmm>-<slug>/plan.md` with the stages, the skill used for each,
and acceptance criteria written as things you can check in a render ("rain is
visible on the window glass", "subject fills 60-70% of frame height").

### 5. Build stage by stage

Read each stage's SKILL.md just before that stage, not all at the start: the
long ones run over a thousand lines and most of a plan is never needed at once.
Include an optional stage only when its `when` condition holds. When
`pipeline-planning` is loaded, its assembly order (block-out, camera, light,
then detail) governs the sequence of work; the load plan only says what to read.

### 6. Check, refine, stop

Take the checkpoints the budget names and inspect every image yourself before
moving on. Spend at most `refinement_passes` fix passes; if the same defect
survives two of them, load the `refinement` capability instead of trying a third
variation. When the budget is spent, deliver what you have and list what is
still wrong. Details: `H/orchestrator/qa-loop.md`.

### 7. Deliver

Put renders and exports in the job folder and report: profile and workflow
chosen, skills used, files written (absolute paths), what was checked, what
remains imperfect, and that the .blend is unsaved unless the user asked to save
it. Under the newo-ether provider, call `release_blender_instance` before the
final reply, including when you stop early.

## Rules for reading upstream skills

Upstream skills were written to be installed on their own. Read them with these
adjustments. The load plan repeats the ones that apply.

- **Paths in the load plan are relative to `H`.** Read `H/upstream/...`.
- **Bare skill names mean siblings.** When an upstream skill says "load
  `blender-lighting`", it means the skill of that name in the same upstream, not
  the same-named one elsewhere. `uv run "H/scripts/harness.py" where <name>`
  shows every match and its path.
- **Skill-relative paths.** When an upstream skill refers to its own folder
  (through a `CLAUDE_SKILL_DIR` variable) or to relative paths such as
  `references/x.md` or `scripts/y.py`, resolve them against the folder of the
  SKILL.md you just read.
- **One server, one tool prefix.** Every mention of `mcp__blender__*`,
  `mcp__Blender__*` or "the Blender MCP" means the harness's single server (see
  "Tool names" above). Translate foreign tool names with the dialect table in
  the load plan.
- **Setup instructions are void.** Ignore any upstream step that installs an
  addon, registers an MCP server, symlinks into `~/.claude/skills`, or starts a
  bridge on another port. The harness did that work once, for one server.
- **Node graphs versus Python.** With the newo-ether provider, shader,
  compositor and geometry node graphs beyond a simple Principled BSDF go through
  its structured node tools (validate, then apply). Meshes, lights, cameras,
  render settings and animation have no structured tool, so the upstream Python
  recipes run through `execute_blender_code` as intended.
- **`upstream/` is read-only.** It holds other people's repositories at pinned
  commits. When an upstream skill tells you to patch a skill file or cut a
  release, record the lesson in the job's report instead; in a clone of the
  harness repository, also add it to `notes/lessons.md`.
- **Output paths.** Upstream examples write to `/tmp/...` or `~/Desktop/...`.
  `/tmp` does not exist for Blender's Python on Windows. Use the absolute path of
  the job folder under `output/` for every render, export and intermediate file.
- **Keys and paid services.** Some skills call paid APIs (Meshy, Hyper3D,
  Sketchfab). Use them only when the user asked for that service and the key is
  already in their environment. Never ask for a key in chat and never write one
  to a file. If it is missing, skip the stage and say so.
- **Downloads** stay inside the profile's `asset_downloads` budget. Prefer CC0
  sources (Poly Haven) and record every downloaded asset in the job's plan or
  report.
