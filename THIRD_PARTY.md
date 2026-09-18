# Third-party components

This repository contains no third-party source. Each upstream is referenced as a
git submodule: the repository stores a URL and a commit id, and the files are
fetched from their owners when you run the installer.

| Path | Upstream | License | Pinned |
| --- | --- | --- | --- |
| `upstream/cc-blender-skill` | https://github.com/RobLe3/cc-blender-skill | MIT | `11016c9a5847` |
| `upstream/blender-claude-mcp` | https://github.com/Gaius114/blender-claude-mcp | MIT | `bb19815283c5` |
| `upstream/blender-skills` | https://github.com/kevinbadi/blender-skills | none published | `b2f0f816d320` |
| `upstream/jithinolickal-blender` | https://github.com/jithinolickal/blender | Apache-2.0 | `6bfca4973e70` |
| `upstream/newo-blender-mcp` | https://github.com/newo-ether/blender-mcp | MIT | `37acac7fd25d` (v1.18.0) |

`uv run scripts/harness.py list upstreams` prints the current values.

## The unlicensed upstream

`kevinbadi/blender-skills` has no license file. Without one, its author keeps
all rights: the public repository can be viewed and cloned under GitHub's terms,
but its files may not be copied into another project or redistributed. For that
reason:

- it is included only as a submodule pointer, never vendored;
- nothing in this repository quotes or adapts its files;
- `registry/skills.yaml` describes its skills in our own words.

If you depend on it, consider asking the author to add a license. If that never
happens, the submodule can be dropped together with its entries in `registry/`.
Most of what it provides has a fallback in `registry/capabilities.yaml`: the
named camera moves fall back to the generic camera and animation skills, and the
PBR texture, studio, product-finish and web-viewer capabilities have one each.
Two optional stages of the `product` workflow have no other provider and would
go with it: `image-to-3d` (photo-to-3D) and `look-variants` (material and HDRI
comparisons).

## Runtime downloads

The installer downloads the Blender extension of the active MCP provider from
its GitHub release and checks it against the SHA-256 in `registry/mcp.yaml`.
The MCP server itself is fetched by `uvx` from the pinned wheel URL (newo-ether)
or from PyPI (`blender-mcp==2.0.0`, ahujasid). Both are MIT licensed.

Skills may download assets at run time (Poly Haven, CC0) or call paid services
(Meshy, Hyper3D, Sketchfab) when you have configured keys and asked for them.
Those services have their own terms.
