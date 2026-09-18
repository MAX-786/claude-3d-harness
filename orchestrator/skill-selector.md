# Skill selector

How a capability becomes a file to read. The logic lives in
`scripts/harness.py resolve`; this page explains it so the output is never a
surprise, and so the registry can be maintained with the same rules.

## Resolution

For each capability in the plan:

1. Take its `provider` (or the provider of the chosen or default variant) from
   `registry/capabilities.yaml`.
2. Skip it if its `requires.mcp` excludes the MCP provider currently in
   `.mcp.json`, or if its file is missing from the submodule.
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
| `chained` | Loaded by another upstream skill by bare name (`via`). Never routed directly; reach it by following its parent. |
| `excluded` | Never loaded: duplicates, superseded prototypes, or skills that need their own bridge or addon. The `reason` is recorded. |

`kind: reference` marks a supporting document that is not a SKILL.md (an MCP
reference page, a knowledge overview). It is routed like a skill.

## Dialects

Upstreams were written against different MCP servers, so the same action has
different tool names. `registry/mcp.yaml` maps each dialect to the canonical
tools of the one server that runs:

| Dialect | Used by | What changes |
| --- | --- | --- |
| `ahujasid` | cc, kb, jo, newo | Nothing: `mcp__blender__*` already matches. |
| `blender-lab` | gaius | `mcp__Blender__*` with another tool surface; summaries and screenshots map to canonical tools, render-to-path and view jumps become small `execute_blender_code` calls. |

A tool an upstream skill mentions that is neither canonical nor mapped does not
exist here. Do the step with `execute_blender_code`, or skip it and say so.

## Transport

Skills marked `direct-socket` bundle node scripts that open the Blender addon
socket (port 9876) themselves. Under the newo-ether provider that path is
unvalidated and sidesteps instance claiming, so the scripts are not run: the
skill is read for its parameters, asset ids and step order, and the steps are
performed with MCP tools. Under the ahujasid provider the scripts work as their
author intended.

## Changing the routing

- Prefer a different provider: swap `provider` and `fallbacks` in
  `registry/capabilities.yaml`. One provider per capability stays the rule.
- New upstream skill after an update: `verify` reports it as drift. Add it to
  `registry/skills.yaml` as `active` (and route it), `chained` or `excluded`.
- New upstream repository: add the submodule, an entry in
  `registry/upstreams.yaml` (with its dialect), catalog its skills, route the
  ones that fill a gap, exclude the ones that duplicate.

Run `uv run scripts/harness.py verify` after every registry edit.
