---
name: blender-harness
description: Entry point for every 3D or Blender task in this repository - modeling, materials, lighting, cameras, rendering, animation, product shots, environments, cinematic scenes, exports. Classifies the job (fast, standard or cinematic), picks a workflow, asks the registry which upstream skills to load, then drives Blender through the single `blender` MCP server with render, inspect and refine checkpoints. Use it whenever the user asks to create, change, light, render, animate or export anything in 3D, even if they never say "Blender".
---

# Blender harness

This repository does not contain 3D skills of its own. It composes several
upstream skill libraries, pinned as git submodules under `upstream/`, behind one
registry. The upstreams overlap (two ship a `blender-lighting`), were written for
three different MCP servers, and one is in Italian. The registry settles all of
that: one provider per capability, one MCP server, and a note for every
adaptation you need to make. So never browse `upstream/` to choose skills
yourself. Ask the registry, then read exactly what it names.

## Procedure

### 1. Classify the job into a profile

| Profile | The request looks like | Spend |
| --- | --- | --- |
| `fast` | One simple object, or a small edit to a scene that already exists | Inline plan, one checkpoint, one fix pass |
| `standard` | Several objects, believable materials and lighting, a composed camera, one deliverable | Plan file, three checkpoints, two fix passes |
| `cinematic` | A full environment or film-quality shot: many asset types, atmosphere, camera motion, "photorealistic" | Full plan, a gate after every stage, four fix passes |

When two profiles fit, take the lower one and say so in one line; the user can
ask for more. An explicit request ("keep it quick", "go all out") always wins.
Edge cases and worked examples: `orchestrator/task-classifier.md`.

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
`orchestrator/workflow-selector.md`.

### 3. Get the load plan

```bash
uv run scripts/harness.py resolve -w <workflow> -p <profile>
uv run scripts/harness.py resolve -w product -p standard --variant camera-animation=perfect-loop
uv run scripts/harness.py resolve -w modeling -p fast --add architecture
uv run scripts/harness.py resolve -c materials lighting -p fast
```

The plan lists, in order, the SKILL.md files to read, the optional stages with
their conditions, alternatives you can add, the budgets of the profile, and the
adaptation notes for the skills it chose. `uv run scripts/harness.py list
capabilities` shows the whole vocabulary.

### 4. Preflight

Read the skills marked `always`. Then confirm Blender is reachable through the
`blender` MCP server (`list_blender_instances`, or `get_scene_info` under the
ahujasid provider) and look at what is already in the scene. If the MCP tools
are absent or Blender does not answer, stop and tell the user what to start.
Do not switch to GUI automation or any other bridge: a second execution path is
exactly what this harness exists to prevent.

### 5. Plan

Follow the `plan` budget. For `standard` and `cinematic`, create
`output/<yyyymmdd-hhmm>-<slug>/plan.md` with the stages, the skill used for each,
and acceptance criteria written as things you can check in a render ("rain is
visible on the window glass", "subject fills 60-70% of frame height").

### 6. Build stage by stage

Read each stage's SKILL.md just before that stage, not all at the start: the
long ones run over a thousand lines and most of a plan is never needed at once.
Include an optional stage only when its `when` condition holds. When
`pipeline-planning` is loaded, its assembly order (block-out, camera, light,
then detail) governs the sequence of work; the load plan only says what to read.

### 7. Check, refine, stop

Take the checkpoints the budget names and inspect every image yourself before
moving on. Spend at most `refinement_passes` fix passes; if the same defect
survives two of them, load the `refinement` capability instead of trying a third
variation. When the budget is spent, deliver what you have and list what is
still wrong. Details: `orchestrator/qa-loop.md`.

### 8. Deliver

Put renders and exports in the job folder and report: profile and workflow
chosen, skills used, files written (absolute paths), what was checked, what
remains imperfect, and that the .blend is unsaved unless the user asked to save
it. Under the newo-ether provider, call `release_blender_instance` before the
final reply, including when you stop early.

## Rules for reading upstream skills

Upstream skills were written to be installed on their own. Under the harness,
read them with these adjustments. The load plan repeats the ones that apply.

- **Bare skill names mean siblings.** When an upstream skill says "load
  `blender-lighting`", it means the skill of that name in the same upstream, not
  the same-named one elsewhere. `uv run scripts/harness.py where <name>` shows
  every match and its path.
- **`${CLAUDE_SKILL_DIR}` and relative paths** (`references/x.md`,
  `scripts/y.py`) resolve against the folder of the SKILL.md you just read. The
  variable is only substituted for installed skills, so substitute it yourself.
- **One server, one tool prefix.** Every mention of `mcp__blender__*`,
  `mcp__Blender__*` or "the Blender MCP" means the single server named `blender`.
  Translate foreign tool names with the dialect table in the load plan.
- **Setup instructions are void.** Ignore any upstream step that installs an
  addon, registers an MCP server, symlinks into `~/.claude/skills`, or starts a
  bridge on another port. That work is done by `scripts/install.ps1`, once, for
  one server.
- **Node graphs versus Python.** With the newo-ether provider, shader,
  compositor and geometry node graphs beyond a simple Principled BSDF go through
  its structured node tools (validate, then apply). Meshes, lights, cameras,
  render settings and animation have no structured tool, so the upstream Python
  recipes run through `execute_blender_code` as intended.
- **`upstream/` is read-only.** It holds other people's repositories at pinned
  commits, and the project settings deny edits there. When an upstream skill
  tells you to patch a skill file or cut a release, write the lesson to
  `notes/lessons.md` instead.
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
