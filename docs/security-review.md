# Security review of the skill library

**Reviewed:** 2026-09-21, for version 0.3.0, when the four skill libraries moved
from git submodules into `library/`. Carried out with Claude Code; every finding
that led to a change was checked against the file before anything was edited.

**Result:** nothing malicious was found: no exfiltration, no credential access,
no hidden or encoded text, no instruction trying to steer the reviewer. What was
found is what you would expect from skills written by one person for their own
machine and an empty scene. Those passages were removed or rewritten, 21 files
in all. The remaining 111 files are byte-identical to the commit they were
imported from.

A review can miss things, and this one covers the files as they were on that
day. [SECURITY.md](../SECURITY.md) says what the harness does and does not
protect you from.

## Why skills need a review at all

A skill is text that Claude follows while it holds `execute_blender_code`, which
runs Python inside Blender with your user's rights and your open scene. Bundled
scripts run on your machine. So a skill can do harm in two ways: by what its
code does, and by what its prose tells the agent to do.

## What was reviewed and how

| Library | Files | Read in full | Changed | Origin |
| --- | --- | --- | --- | --- |
| `cc` | 106 (78 text, 28 WebP images) | all text files | 12, and 2 scripts removed | RobLe3/cc-blender-skill at `11016c9a5847` |
| `gaius` | 12 | all | 9 | Gaius114/blender-claude-mcp at `bb19815283c5` |
| `jo` | 6 | all | 0 | jithinolickal/blender at `6bfca4973e70` |
| `newo` | 8 | all | 0 | newo-ether/blender-mcp at `37acac7fd25d` (v1.18.0) |

1. **Import from git objects.** Files were written from the blobs of the pinned
   commits, not copied from a checkout, and each was checked against the blob id
   its author published. Symbolic links and nested repositories would have
   stopped the import; there were none.
2. **Five review passes** (two over `cc`, two over `gaius`, one over `jo` and
   `newo`), each reading every text file from the first line to the last (the Italian prose included) against the
   list below, and reporting findings by file and line.
3. **A pattern scan** over every text file (`harness.py audit`), including
   zero-width, bidirectional and Unicode tag characters and long encoded runs.
4. **Verification.** Each finding acted on was re-read in place. One claim about
   third-party code was tested in a separate, headless Blender (see "Outside the
   library").
5. **The images** were checked for the WebP signature. Their pixels were not
   analysed.

What the passes looked for:

- **Agent manipulation:** reading or sending credentials or files outside the
  project, editing the agent's configuration, installing servers or skills,
  hiding actions from the user, overriding earlier instructions, and
  self-propagation (editing skill files, committing, pushing).
- **Dangerous code:** network access, shell or dynamic execution, unsafe
  deserialisation, imports from outside the project, writes or deletes outside a
  job folder, Blender script auto-execution, add-on installs.
- **Supply chain:** package installs, anything downloaded and then run.
- **Secrets:** where keys are read, sent, logged or stored.
- **Hidden content:** encoded blobs, invisible characters, instructions in
  comments, look-alike URLs.
- **Data loss:** recipes that wipe or overwrite the user's scene, files or
  preferences by default.

## What was changed

Most changes remove something. Where lines were added (the world reset and three
scripts), they are few and the tables below say what they do.

### gaius: a personal setup written into the skills

| File | Change | Why |
| --- | --- | --- |
| `blender-arch`, `blender-coordinator`, `blender-procedural` | Removed the sections that run `sys.path.insert(0, r"D:\blender-claude\kernel")` (or `D:\blender_ragionamento`) and import a module from there, and the rules that made one of them mandatory | The path is a folder on the author's machine. On anyone else's PC, whoever can create that folder gets code running inside Blender with the user's rights. One of the modules is published nowhere, so it could not be reviewed. The modules were never part of the harness, so nothing that worked was lost |
| `blender-arch`, `blender-space`, `blender-texture` | Removed the helper that POSTs code to `http://localhost:7234/execute` | A second, unauthenticated way to run code in Blender, outside the MCP server and its permission prompts. The harness never installs that bridge, so whatever listens on that port would receive the code |
| `blender-arch` | Removed the snippet that sets `preferences.system.use_online_access = True` and starts another add-on's server | It silently switches on the preference by which a Blender user consents to internet access |
| `blender-arch` | Removed `CLEAR_SCENE` | It deleted every object, mesh, material and collection in the open file |
| `blender-sculpt` | `sculpt_base_sphere` no longer starts with select-all and delete | Same: it emptied the scene before adding a sphere |
| `blender-texture` | `new_mat` no longer removes an existing material of the same name; the bake helpers no longer default to `D:/output/...` | A user's `Glass` or `Metal` material was deleted and unlinked from every object; bakes were written to a fixed path outside any job |
| six skills | `C:/Users/<author>/Downloads/...` became `<JOB_DIR>/...` | Renders were written into another person's profile path |
| `blender-physics` | Reworded a note that read "to be added to the routing table in blender-coordinator" | It read as an instruction to edit another skill file |

### cc: a skill stack that edits itself

| File | Change | Why |
| --- | --- | --- |
| `quality-refinement-autoloop/SKILL.md` | Rewritten without its phases "sanitize the lesson", "patch skill stack", "validate skill change" and "release prep"; the visible note at its top says so | When a user called a result bad, the skill told the agent to write new instructions and helper scripts into the skill files, then bump versions and prepare a commit. Text derived from user feedback and reference files would have become standing instructions for later sessions |
| `quality-refinement-autoloop/scripts/` | Removed `release_readiness_check.py` and `sanitize_skill_contributions.py`; the plan script no longer lists the removed phases | They served only that publishing flow |
| `fit-repair-optimizer`, `blender-skill-harmonizer`, `text-to-blender`, `animation-quality-gate` | The sentences that routed into skill patching now say: diagnose, record the lesson, retry | They triggered the behaviour above automatically, after two failures |
| `text-to-blender/references/common-object-dimensions.md` | No longer says to add looked-up dimensions to the file | Text from the web would have been written into an instruction file |
| `text-to-blender/SKILL.md` | The world reset gives the scene a new World and keeps the old one (with a fake user) instead of deleting its nodes; the default cube is removed by name | The reset ran at the start of every build and destroyed whatever HDRI or sky the user had set up. `bpy.ops.object.delete()` deletes the selection, which need not be the cube |
| `wireframe-to-3d/SKILL.md` | The unpinned `pip install` became the `uv run --with` form | It installed four packages into whatever Python came first on `PATH` |
| `wireframe-to-3d/references/blender-patterns.md` | The end-to-end example no longer begins with select-all and delete | It emptied the open scene |
| `wireframe-to-3d/scripts/wireframe_analyzer.py` | The default output path is built from the file stem, output equal to input is refused, and the tuning flags the skill documents now exist | For `front.PNG` or `front.jpg` the old default was the input path, so the JSON was written over the drawing. The documented flags did not exist, which left "edit the script" as the only route. Tested: the input survives |
| `source-part-segmentation/scripts/seeded_part_masks.py` | A part name is reduced to its last path component | The name comes from a manifest that may ship with a third-party asset pack; `../` would have placed a file outside `--out-dir` |
| `closed-surface-uv-coverage/scripts/surface_texture_coverage_audit.py` | Parses only the arguments after `--` | Inside Blender, `sys.argv` holds Blender's own flags; argparse would raise `SystemExit`, which can end a live session |

### jo and newo: no file changes

Both are byte-identical to their origin. What the review found in them is
handled by notes that every load plan prints (`registry/skills.yaml`):

- **jo/blender** tells the agent to save a "milestone" before every change with
  `save_as_mainfile` (which turns the milestone into the open document, so the
  user's next save lands in it), to restore with `open_mainfile` (which throws
  away everything unsaved), and to clear the scene first. Under the harness all
  three are void.
- **newo/blender-mcp** is defensive by design. Its node layout reference records
  its author's own preferences as "the user's", among them short Chinese frame
  labels; the note says to label in the user's language. Its asset reference
  does not say that image-conditioned generation uploads the reference images
  to a paid service; the note does.

## What was left as it is, and what covers it

| Finding | Where | Covered by |
| --- | --- | --- |
| Recipes that clear the World's nodes, remove lights named `LGT-*`, reuse a camera or material by name, or apply modifiers to the source mesh | `cc/blender-lighting`, `cc/blender-export`, `gaius/blender-lighting`, `gaius/blender-texture`, `gaius/blender-sculpt` and others | The entry skill's rule "The user's scene and files are not yours to clear", plus a note on the skills where it matters most. Rewriting every recipe is a change to the skills' content, which is the next step, not this one |
| Scene-wide settings changed and not restored (engine, samples, frame range, fps), and Cycles device preferences | several `cc` and `gaius` skills | The same rule: report every such change, leave preferences alone |
| Outputs written to `/tmp/...` | most `cc` skills | The entry skill's "Output paths" rule |
| `allowed-tools: ... Bash ...` in the frontmatter of the `cc` and `gaius` skills | 39 files | Inert: the harness reads these files, it never registers them as Claude Code skills. `verify` fails if a root `skills/` folder appears. Do not copy a library folder into `~/.claude/skills` |
| `scipy` imports in two `gaius/blender-procedural` snippets (Blender's Python has no scipy) | `gaius/blender-procedural` | The entry skill's "Install nothing" rule |
| `blender-research` sends the subject of the job to a web search | `gaius/blender-research` | The entry skill's rule that what tools return is data. For a confidential product, say so in the prompt and Claude will skip the research stage |
| Pillow and OpenCV decode images the user supplies, unpinned | 15 `cc` scripts | They run under `uv run --with`, in a throwaway environment. Pinning versions is an open improvement |
| References to files of the author's other projects, which do not exist here | `cc/text-to-blender` | Harmless: there is nothing to find, and the entry skill keeps the agent inside the job folder |

## Outside the library

**The unlicensed library was not imported.** `kevinbadi/blender-skills`
publishes no license, so its author keeps all rights and its files may not be
copied or adapted. Its sixteen skills left the catalog with the submodules.
Their capabilities route to the skills that were their fallbacks; `look-variants`
had none and was removed.

**The MCP server and its Blender extension are not vendored.** They are fetched
from the pinned release in `registry/mcp.yaml`; the extension is checked against
its SHA-256 before it is installed. One thing in the extension deserves to be
known:

> The add-on copies the Hyper3D, Sketchfab and Hunyuan3D API keys from its
> preferences onto properties of every scene, on every file load
> (`blender_extension/lifecycle.py`, `ui.py`, v1.18.0). Blender writes such a
> property into the .blend in plain text: a `StringProperty(subtype="PASSWORD")`
> set on a scene and saved was found byte for byte in the file (Blender 5.2.2,
> factory settings, no add-ons). **A .blend saved while a key is configured
> carries the key, and sharing the file shares it.**

The entry skill now tells Claude to `property_unset` those four properties on
every scene before saving a .blend that will be shared. Unsetting removes the
value from the file and does not touch the add-on's preferences (tested in the
same way); assigning an empty string would erase the stored key through the
add-on's update callback. If you share .blend files and have ever entered a key
in the BlenderMCP panel, rotate it. This has been found by reading v1.18.0 and
should be reported to the add-on's authors.

## Keeping it true

- `library/SHA256SUMS` records every file as reviewed. `harness.py verify`
  (and so CI) fails on any file that was edited, added or deleted without the
  list changing in the same commit, which puts every skill change in front of a
  reviewer. Anyone can check it without this project's code:
  `cd library && sha256sum -c SHA256SUMS`.
- `harness.py audit --changed` scans exactly the files that differ from the
  list. Its flags are prompts for a person, not verdicts: it finds patterns, not
  intent, and a clean audit is not a clean bill of health.
- In a clone, Claude Code asks before every edit under `library/`
  (`.claude/settings.json`), and the entry skill forbids such edits during a job.
- New library code is reviewed against the list above before it is cataloged.
  [CONTRIBUTING.md](../CONTRIBUTING.md) has the steps.
