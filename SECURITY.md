# Security

## What this project runs on your machine

The harness lets Claude Code drive Blender. Three things follow from that, and
they are worth knowing before you install it:

- **`execute_blender_code` runs Python inside Blender** with your user's rights.
  Claude Code asks before each call unless you chose to always allow it.
- **The 3D skills are other people's text.** They live in five repositories
  under `upstream/`, and Claude follows them as instructions while it has that
  code-execution tool.
- **The MCP server and its Blender extension are third-party code**, fetched
  from a pinned GitHub release.

## What the harness does about it

- Every upstream is a git submodule at a commit a person reviewed
  (`cataloged_at` in `registry/upstreams.yaml`). Nothing updates by itself; a
  weekly workflow only reports that a pin is behind.
- `harness.py update` prints a compare link per upstream and audits the changed
  files for network calls, shell or dynamic execution, credentials, agent-config
  tampering, installs and destructive file operations.
- The Blender extension is checked against the SHA-256 in `registry/mcp.yaml`
  before it is installed. The server wheel's SHA-256 is recorded there too.
- `upstream/` is edit-denied in `.claude/settings.json`, so in a clone Claude's
  file-editing tools refuse a skill's request to rewrite skill files.
- Skills that open their own socket to Blender, or need their own bridge, are
  marked or excluded in `registry/skills.yaml` and never run as written.
- The MCP server's telemetry is switched off in the generated `.mcp.json`.
- The tests never collect or import anything under `upstream/`.

## What it does not do

It does not sandbox Blender or Claude Code. The audit flags are prompts for a
human review, not verdicts, and a review can miss things. If you would not run
a Python script from a stranger, keep the permission prompt for
`execute_blender_code` switched on and read what it is about to run.

## Reporting a vulnerability

Please report privately, not in a public issue: open the repository's
**Security** tab and choose **Report a vulnerability**
(https://github.com/MAX-786/claude-3d-harness/security/advisories/new).

Useful to include: what an attacker controls (a prompt, a skill file, an asset,
a release asset), what they gain, and the output of
`uv run scripts/harness.py doctor`.

If the problem is in an upstream skill or in the MCP server, report it to that
project as well. Tell us too: the harness can pin an earlier commit, exclude the
skill or switch the provider the same day, which is faster than waiting for an
upstream fix.

Only the latest release is supported.
