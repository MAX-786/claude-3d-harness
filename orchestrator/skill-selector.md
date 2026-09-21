# Skill selector

How a capability becomes a file to read. The logic lives in
`scripts/harness.py resolve`; this page explains it so the output is never a
surprise, and so the registry can be maintained with the same rules.

## Resolution

For each capability in the plan:

1. Take its `provider` (or the provider of the chosen or default variant) from
   `registry/capabilities.yaml`.
2. Skip it if its `requires.mcp` excludes the MCP provider currently in
   `.mcp.json`, or if its file is missing from `library/`.
3. Otherwise walk `fallbacks` in order under the same test.
4. If nothing qualifies, the capability is reported as UNAVAILABLE and the job
   proceeds without that skill (for example `mcp-usage` under the ahujasid
   provider, where the execution-core skill already covers the server).

Every substitution is printed under SUBSTITUTIONS, so you always know when you
are not on the canonical provider.

## Fallbacks at run time

The resolver switches providers only for availability. Switching for quality is
your call, under one rule: **never load a second provider of the same capability
unless the first has failed twice on the same defect.** Two lighting skills in
one context produce blended advice and naming conflicts (`LGT-key` versus the
other library's conventions). When you do switch, say so in the report.

## Catalog statuses

| Status | Meaning |
| --- | --- |
| `active` | Routable. Must be reachable from at least one capability. |
| `chained` | Loaded by another library skill by bare name (`via`). Never routed directly; reach it by following its parent. |
| `excluded` | In the library but never loaded. The `reason` is recorded. No entry uses it today: duplicates and skills that need their own bridge were not imported. |

`kind: reference` marks a supporting document that is not a SKILL.md (an MCP
reference page, a knowledge overview). It is routed like a skill.

## Dialects

The libraries were written against different MCP servers, so the same action has
different tool names. `registry/mcp.yaml` maps each dialect to the canonical
tools of the one server that runs:

| Dialect | Used by | What changes |
| --- | --- | --- |
| `ahujasid` | cc, kb, jo, newo | Nothing: `mcp__blender__*` already matches. |
| `blender-lab` | gaius | `mcp__Blender__*` with another tool surface; summaries and screenshots map to canonical tools, render-to-path and view jumps become small `execute_blender_code` calls. |

A tool a library skill mentions that is neither canonical nor mapped does not
exist here. Do the step with `execute_blender_code`, or skip it and say so.

## Changing the routing

- Prefer a different provider: swap `provider` and `fallbacks` in
  `registry/capabilities.yaml`. One provider per capability stays the rule.
- New skill in `library/`: `verify` reports it as drift until it is in
  `registry/skills.yaml` as `active` (and routed), `chained` or `excluded`.
- New library: it needs a license that allows copying. Import only the skill
  folders, review them (CONTRIBUTING.md, "Adding a library"), add an entry in
  `registry/libraries.yaml` with its origin, commit, license and dialect,
  catalog its skills, route the ones that fill a gap, leave out the ones that
  duplicate, then record the checksums.

Run `uv run scripts/harness.py verify` after every registry edit.
