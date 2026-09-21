# Third-party components

The MIT license in [LICENSE](LICENSE) covers the files this project wrote. The
skill libraries under `library/` were written by other people. Four are included
under the open licenses they were published with; each of those license files
sits next to its library, unchanged, as `library/<key>/LICENSE`. **One,
`library/kb`, is not under an open license at all**: see below before you reuse
anything from this repository.

| Path | Imported from | License | Copyright | Commit |
| --- | --- | --- | --- | --- |
| `library/cc` | https://github.com/RobLe3/cc-blender-skill (`plugin/skills`, one file of `knowledge/`) | MIT | (c) 2026 RobLe3 | `11016c9a5847` |
| `library/gaius` | https://github.com/Gaius114/blender-claude-mcp (`skill`) | MIT | (c) 2026 Josia | `bb19815283c5` |
| `library/kb` | https://github.com/kevinbadi/blender-skills (15 skill folders) | **none published; included by permission** | kevinbadi, all rights reserved | `b2f0f816d320` |
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
- 9 files of `library/kb` were edited, its 7 Node scripts were removed, and one
  file (`threejs-export/assets/viewer.html`) was added, carrying the HTML
  template that used to live inside one of those scripts. Each rewritten skill
  says so at its top.

## `library/kb` is not open source

`kevinbadi/blender-skills` publishes no license: no license file, nothing in its
README, none reported by GitHub (checked 2026-09-21). Without one its author
keeps all rights, and the repository being public changes nothing about that.

Its files are in this repository, and were edited, **on the maintainer's
statement that the author gave permission privately**. The text of that
permission is not published, so nobody but the two of them can say what it
covers. What follows from that:

- The MIT license of this repository does **not** cover `library/kb`. It gives
  you no right to copy, modify or redistribute those files outside this project.
  `library/kb/LICENSE` says the same, and `harness.py verify` prints a reminder.
- If you fork this repository or reuse parts of it, leave `library/kb` out, or
  ask its author for permission of your own. The harness keeps working without
  it: every capability it provides has a fallback except `look-variants`
  (`registry/capabilities.yaml`).
- `blender-toolkit/` in that repository is a copy of a third author's project.
  Its author could not give permission for it, and it was not imported.
- If the author publishes a license, this section and `library/kb/LICENSE`
  should be replaced by it.

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
