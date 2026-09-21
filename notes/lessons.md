# Lessons

`library/` is never edited during a job, so lessons that a skill would write
back into its own files land here instead. One entry per lesson: date, the job,
what went wrong, what fixed it, and which skill (`<key>/<name>`) it concerns.
Entries that keep recurring are worth a reviewed fix to the skill in `library/`
(see CONTRIBUTING.md), or a routing change in `registry/capabilities.yaml`.

`harness.py resolve` reads this file: every load plan ends with the entries that
concern its skills, by line number. For that, an entry is one top-level bullet
that opens with `**<key>/<name> — short title.**`, or with `**short title.**`
when it concerns no single skill. `harness.py verify` warns when the id is not
in the catalog.

## 2026-09-18 — job 20260918-2152-anime-rooftop-study (cinematic, Blender 5.2.2, newo-ether v1.18.0)

Paths under `output/` below are in that job's folder, which git ignores; they exist on the machine that ran it.

- **newo/blender-mcp — deleting pre-existing datablocks.** `execute_blender_code` reports
  `StructRNA of type Object has been removed` (or `Collection`/`Material`) whenever the code removes a datablock
  that existed before the call, even inside a function. The edit itself persists (`rollback_scope: none`), but the
  printed output is lost. Fix: treat it as cosmetic, verify with a separate read call. Do not use
  `transaction=true` to avoid it: that mode also rolls back the new datablocks.
- **newo/blender-mcp — `result` is not returned.** Only stdout comes back; `print()` what you need.
- **newo/blender-mcp — socket refs in patches use identifiers, not labels.** Group interface sockets are
  `Socket_N`; Math inputs are `Value`, `Value_001`, `Value_002`. The validator's `stale_socket_id` diagnostic
  names the right identifier — fix from it rather than guessing.
- **newo/blender-mcp — pinned Node Editor + owner-copy transaction.** `apply_node_tree_patch` commits by copying
  the material and remapping users. With `keep_backup=false` the old tree is freed while a Node Editor pinned to
  it (for `inspect_node_layout(refresh=true)`) still points at it. Shortly afterwards the add-on stopped answering
  (heartbeat stalled, Blender idle and responsive, even autosave stopped). Fix for next time: unpin or repoint the
  editor before applying a patch to the pinned tree, or keep the backup so the old tree stays alive.
- **cc/blender-rendering — OptiX.** On this RTX 3050 Laptop OptiX kernels fail to load
  (`OPTIX_ERROR_INTERNAL_COMPILER_ERROR`). Root cause (confirmed 2026-09-19): the NVIDIA driver is 566.07, and
  the Blender 5.2 manual (render/cycles/gpu_rendering) requires driver **575 or newer** for OptiX; Blender still
  lists the OptiX device, so the failure only appears at kernel compile time. OSL was off, so it was not the
  trigger. Fix: update the driver to 575+. Until then CUDA works, and OIDN already runs on the GPU
  (`denoising_use_gpu`; all RTX cards qualify), so denoise quality is not affected; OptiX would mainly speed up
  path tracing. Check `nvidia-smi` against the manual's minimum before choosing OptiX.
- **cc/blender-lighting (via Cycles) — light linking from Python.** A receiver collection with INCLUDE children,
  set on a light via `light_linking.receiver_collection`, was not honoured in renders (not even an empty receiver
  set). Two tries failed on the same defect, so the fix was changing approach: a narrow spot aimed so its cone
  hits the roof before the door, and `visible_diffuse=False` on the emissive billboard mesh.
- **Poly Haven multi-part models.** Parts (pot + soil + leaves, clock + hands) carry relative offsets; join them
  before zeroing locations or instancing, otherwise the parts separate.
- **Orientation checks in dim scenes.** A prop that looks "backwards" in a dark render may just be unlit. Check
  the face normal against the camera direction numerically before rotating (a wrong 180° "fix" was reverted).
- **newo/blender-mcp — Poly Haven model import.** `image.unpack(method='WRITE_ORIGINAL')` wrote into Blender's
  temp pack path, so the job's asset folders stayed empty. Fix: write `packed_file.data` to the target folder,
  `unpack(method='REMOVE')`, set `filepath`, `reload()`. Images with 0 users are not saved: load textures
  meant for later patches with a fake user and clear it once materials use them.
- **newo/blender-mcp — Poly Haven after a relaunch.** The add-on's Poly Haven toggle reset to off
  ("Unknown command type: download_polyhaven_asset"), and `api.polyhaven.com` answered Python `urllib` with 403.
  `curl` against `https://api.polyhaven.com/files/<id>` works; record the source as usual.
- **newo/blender-mcp — layout sizes are measured, not guessed.** Build a throwaway tree with one node per
  type/config, show it in a Node Editor, `inspect_node_layout(refresh=true)`, and keep the sizes
  (`output/20260918-2152-anime-rooftop-study/scripts/node_sizes.json`). An unlinked expandable vector input
  (Vector Math, Separate XYZ, Mapping, GN Points/Instance on Points) adds 62 canvas units. Compositor node
  sizes differ per menu value: measure after the first apply and relayout with the measured sizes.
- **newo/blender-mcp — layout rules as a constraint solve.** Compact stacks (gap 20-60), ordered fan-in across
  frames and Group Input socket alignment are all difference constraints; Bellman-Ford finds positions or a
  negative cycle, and the cycle names the column order to change
  (`output/20260918-2152-anime-rooftop-study/scripts/matgen.py`). 30 graphs, incl. a
  48-node facade and a GN tree with three Group Inputs, passed `audit_node_layout` first time this way.
- **newo/blender-mcp — incremental patches.** Keep each apply's `created_nodes` map; diff the old and new graph
  specs into add/remove ops plus `set_node_layout` on real names (frame parents by real name too).
  PowerShell `Set-Content -Encoding utf8` writes a BOM: read such JSON with `utf-8-sig`.
- **newo/blender-mcp — GN modifier inputs on a shared tree** need `shared_tree_policy: "mutate_shared"`
  (`allow` is not a value), even though only modifier inputs change.
- **newo/blender-mcp — scene compositor.** Blender 5.2 compositor: Glare type/quality and Color Balance mode
  are menu sockets; the output is `Final Render Result` (`input:0:Socket_0`). Move the Node Editor off the
  compositor tree before applying (the apply swaps in a copy).
- **cc/blender-lighting — lights inside bulb meshes.** A light placed inside an emissive bulb mesh is blocked by
  it; set the bulb's `visible_shadow = False`. Lights with `visible_camera = False` still show as discs through
  glass via transmission rays; set `visible_transmission = False` on every light. Closed glass also blocks
  shadow rays, so light from a sign outside a window needs an area light just inside the glass.
- **cc/blender-lighting — spot intensity.** Blender spots use point-light intensity (P/4pi per steradian): 150 W
  at 2.4 m gave ~1.6 W/m², about 20x less than a 55 W desk lamp at 0.35 m; the wet slab needed 600 W to read.
- **cc/knowledge-compositing — Mist pass through glass.** The Mist pass stops at the first glass surface, so a
  mist fog seams between the glazed and open halves of a door. Put aerial haze in the far materials instead
  (Camera Data > View Distance > Mix Shader toward the horizon-glow colour).
- **cc/knowledge-compositing — Lift/Gamma/Gain on scene-linear.** A 6% blue lift turned a night interior
  violet and banded (most values are below 0.2). Keep the node factor around 0.3 and grade on top of AgX.
- **Poly Haven `american_walnut_veneer` is grey-toned** (tagged "gray"): recolour via a luminance ColorRamp
  rather than Hue/Saturation, which cannot add hue to grey.
