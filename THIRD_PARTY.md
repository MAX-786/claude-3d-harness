# Third-party components

The MIT license in [LICENSE](LICENSE) covers the files this project wrote. The
skill libraries under `library/` were written by other people and are included
under the licenses they were published or licensed with. Each library's license
file sits next to it as `library/<key>/LICENSE`.

| Path | Imported from | License | Copyright | Commit |
| --- | --- | --- | --- | --- |
| `library/cc` | https://github.com/RobLe3/cc-blender-skill (`plugin/skills`, one file of `knowledge/`) | MIT | (c) 2026 RobLe3 | `11016c9a5847` |
| `library/gaius` | https://github.com/Gaius114/blender-claude-mcp (`skill`) | MIT | (c) 2026 Josia | `bb19815283c5` |
| `library/kb` | https://github.com/kevinbadi/blender-skills (15 skill folders) | MIT | (c) 2026 kevinbadi | `b2f0f816d320` |
| `library/jo` | https://github.com/jithinolickal/blender (`skills`) | Apache-2.0 | jithinolickal | `6bfca4973e70` |
| `library/newo` | https://github.com/newo-ether/blender-mcp (`skills`) | MIT | (c) 2025 Siddharth Ahuja | `37acac7fd25d` (v1.18.0) |

`uv run scripts/harness.py list libraries` prints the current values, and
`registry/libraries.yaml` says what was left out of each import.

## `library/kb` carries no LICENSE file at its origin

`kevinbadi/blender-skills` has no LICENSE file, nothing about licensing in its
README, and GitHub reports none (checked 2026-09-21). Without a published grant,
its author keeps all rights by default, and the repository being public does
not change that.

`library/kb/LICENSE` was written for this repository: it carries the standard
MIT text, on the author's statement, given directly to this project's
maintainer, that the work is MIT licensed. If you rely on that grant
independent of this repository — a fork, a reuse elsewhere — get it from the
author directly, the same way.

`blender-toolkit/` in that origin repository is a copy of a third author's
project; kevinbadi cannot license it on their own behalf, and it was not
imported.

## What was changed after import

- `library/jo` and `library/newo` are byte-identical to the commits above. The
  Apache-2.0 library ships no NOTICE file. If a file of `library/jo` is ever
  edited, Apache-2.0 section 4(b) requires a prominent notice in that file
  saying it was changed.
- 12 files of `library/cc` and 9 of `library/gaius` were edited, and 2 scripts of
  `library/cc` were removed, for the security reasons listed file by file in
  [docs/security-review.md](docs/security-review.md). The rewritten
  `quality-refinement-autoloop/SKILL.md` says so at its top.
- 9 files of `library/kb` were edited, its 7 Node scripts were removed, and one
  file (`threejs-export/assets/viewer.html`) was added, carrying the HTML
  template that used to live inside one of those scripts. Each rewritten skill
  says so at its top.

## Runtime downloads

The installer downloads the Blender extension of the active MCP provider from
its GitHub release and checks it against the SHA-256 in `registry/mcp.yaml`.
The MCP server itself is fetched by `uvx` from the pinned wheel URL (newo-ether)
or from PyPI (`blender-mcp==2.0.0`, ahujasid). Both are MIT licensed. These are
the only things the harness fetches; the skill library is already here.

Skills may download assets at run time (Poly Haven, CC0) or call paid services
(Meshy from two `kb` skills; Hyper3D, Hunyuan3D and Sketchfab through the MCP
server) when you have configured them and asked for them. Those services have
their own terms, and the photos you give them leave your machine.

The web viewer that `kb/threejs-export` writes loads Three.js 0.170.0 (MIT) from
cdn.jsdelivr.net when the page is opened.
