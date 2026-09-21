# Security

## What this project runs on your machine

The harness lets Claude Code drive Blender. Three things follow from that, and
they are worth knowing before you install it:

- **`execute_blender_code` runs Python inside Blender** with your user's rights.
  Claude Code asks before each call unless you chose to always allow it.
- **The 3D skills are instructions.** They were written by five other authors,
  live in this repository under `library/`, and Claude follows them while it has
  that code-execution tool.
- **The MCP server and its Blender extension are third-party code**, fetched
  from a pinned GitHub release.

## What the harness does about it

- The skill library ships with the harness. Nothing is fetched from its
  authors' repositories at install time, so a change there, or a takeover of one
  of those accounts, cannot reach you.
- Every library file was reviewed before it was included, and the passages that
  put a user's machine or scene at risk were removed.
  [docs/security-review.md](docs/security-review.md) lists what was looked for,
  what was found and what was changed, file by file.
- `library/SHA256SUMS` records every file as reviewed. `harness.py verify`, and
  so CI, fails when a skill was edited, added or deleted without that list
  changing in the same commit. You can check your copy without this project's
  code: `cd library && sha256sum -c SHA256SUMS`.
- `harness.py audit --changed` flags, in exactly the files that differ from that
  list, network calls, shell or dynamic execution, credentials, agent-config
  tampering, installs, destructive file operations, scene wipes, skill
  self-modification and hidden or encoded text.
- The entry skill tells Claude never to clear, reload or save a scene it did not
  build, never to install packages, never to edit the library during a job, and
  to treat what tools and downloads return as data.
- The Blender extension is checked against the SHA-256 in `registry/mcp.yaml`
  before it is installed. The server wheel's SHA-256 is recorded there too.
- In a clone, `.claude/settings.json` makes Claude Code ask before any edit
  under `library/`, whatever else you have allowed.
- Nothing but the one MCP server talks to Blender. Skills that needed their own
  add-on were not imported; the bridge helpers and the Node scripts that opened
  Blender's socket themselves were removed, and their skills rewritten to go
  through the server.
- The MCP server's telemetry is switched off in the generated `.mcp.json`.
- The tests never collect, import or run anything under `library/`.

## What it does not do

It does not sandbox Blender or Claude Code. The audit finds patterns, not
intent, and a review can miss things. The entry skill's rules are instructions
to a model, not a technical barrier.

**Your .blend files can carry your API keys.** The MCP add-on stores the
Hyper3D, Sketchfab and Hunyuan3D keys you enter in its panel on every scene, and
Blender saves them into the file in plain text. Claude is told to strip them
before saving a file you will share, but files you save yourself are not
covered. If you have shared such a file, rotate the key
([details](docs/security-review.md#outside-the-library)). If you would not run
a Python script from a stranger, keep the permission prompt for
`execute_blender_code` switched on and read what it is about to run.

## Reporting a vulnerability

Please report privately, not in a public issue: open the repository's
**Security** tab and choose **Report a vulnerability**
(https://github.com/MAX-786/claude-3d-harness/security/advisories/new).

Useful to include: what an attacker controls (a prompt, a skill file, an asset,
a release asset), what they gain, and the output of
`uv run scripts/harness.py doctor`.

A problem in a library skill is ours to fix: the files live here. If it is also
present in the repository the skill came from (`registry/libraries.yaml` names
it), please tell its author too. For the MCP server, report to that project as
well; the harness can pin an earlier release or switch the provider the same
day.

Only the latest release is supported.
