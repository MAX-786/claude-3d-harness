# Third-party components

The MIT license in [LICENSE](LICENSE) covers the files this project wrote. The
skill libraries under `library/` were written by other people and are included
under the licenses they published them with. Each library's license file sits
next to it, unchanged, as `library/<key>/LICENSE`.

| Path | Imported from | License | Copyright | Commit |
| --- | --- | --- | --- | --- |
| `library/cc` | https://github.com/RobLe3/cc-blender-skill (`plugin/skills`, one file of `knowledge/`) | MIT | (c) 2026 RobLe3 | `11016c9a5847` |
| `library/gaius` | https://github.com/Gaius114/blender-claude-mcp (`skill`) | MIT | (c) 2026 Josia | `bb19815283c5` |
| `library/jo` | https://github.com/jithinolickal/blender (`skills`) | Apache-2.0 | jithinolickal | `6bfca4973e70` |
| `library/newo` | https://github.com/newo-ether/blender-mcp (`skills`) | MIT | (c) 2025 Siddharth Ahuja | `37acac7fd25d` (v1.18.0) |

`uv run scripts/harness.py list libraries` prints the current values, and
`registry/libraries.yaml` says what was left out of each import.

## What was changed after import

- `library/jo` and `library/newo` are byte-identical to the commits above. The
  Apache-2.0 library ships no NOTICE file. If a file of `library/jo` is ever
  edited, Apache-2.0 section 4(b) requires a prominent notice in that file
  saying it was changed.
- 12 files of `library/cc` and 9 of `library/gaius` were edited, and 2 scripts of
  `library/cc` were removed, for the security reasons listed file by file in
  [docs/security-review.md](docs/security-review.md). The rewritten
  `quality-refinement-autoloop/SKILL.md` says so at its top.

## A library that is not included

`kevinbadi/blender-skills` was referenced by earlier versions as a git submodule.
It publishes no license, so its author keeps all rights: the repository can be
viewed and cloned under GitHub's terms, but its files may not be copied into
another project, adapted or redistributed. It was therefore not imported, and
nothing in this repository quotes or adapts its files. If its author adds a
license, it can be imported like the others.

What it provided now routes to the skills that were its fallbacks
(`registry/capabilities.yaml`). Two things have no replacement yet: named camera
moves as separate variants, and comparison renders across materials or HDRIs.

## Runtime downloads

The installer downloads the Blender extension of the active MCP provider from
its GitHub release and checks it against the SHA-256 in `registry/mcp.yaml`.
The MCP server itself is fetched by `uvx` from the pinned wheel URL (newo-ether)
or from PyPI (`blender-mcp==2.0.0`, ahujasid). Both are MIT licensed. These are
the only things the harness fetches; the skill library is already here.

Skills may download assets at run time (Poly Haven, CC0) or call paid services
through the MCP server (Hyper3D, Hunyuan3D, Sketchfab) when you have configured
them and asked for them. Those services have their own terms.
