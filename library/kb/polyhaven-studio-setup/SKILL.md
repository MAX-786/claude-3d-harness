---
name: polyhaven-studio-setup
description: Set up a professional product photography studio in Blender using PolyHaven HDRIs and PBR ground materials. Trigger when asked to create a studio setup, add HDRI lighting, set up product photography, or create a showroom scene.
---

# PolyHaven Studio Setup

Product photography studio: a PolyHaven HDRI for environment lighting and, optionally, a PBR ground plane — dramatically better reflections than manual lights.

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> sent it Python built from command-line text. The same steps now go through the MCP server, where each one is visible
> and asks for permission. See `docs/security-review.md`.

## Prerequisites

- **Blender MCP** connected, with **PolyHaven** enabled in the add-on sidebar (`get_polyhaven_status`)

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `hdri` | PolyHaven HDRI asset ID | `studio_small_09` |
| `ground` | PolyHaven texture ID for the ground plane (optional) | none |
| `resolution` | Asset resolution: 1k, 2k, 4k | `2k` |
| `strength` | HDRI background strength | `1.0` |
| `rotation` | HDRI rotation in degrees | `0` |
| `ground_size` | Ground plane size | `10` |

## Flow

### Step 1: Keep the World that is already there

The add-on's HDRI download rebuilds the first World in the file in place. If the scene has a World this job did not
make, copy it first so it can be given back:

```python
import bpy
scene = bpy.context.scene
if scene.world and not scene.world.name.startswith("KEEP-"):
    keep = scene.world.copy()
    keep.name = "KEEP-" + scene.world.name
    keep.use_fake_user = True   # survives a save with no scene pointing at it
    print("kept:", keep.name)
```

To undo the studio later: `scene.world = bpy.data.worlds["KEEP-<name>"]`.

### Step 2: Download and apply the HDRI

`download_polyhaven_asset(asset_id=<hdri>, asset_type="hdris", resolution=<resolution>, file_format="hdr")`

### Step 3: Strength and rotation

```python
import bpy, math

STRENGTH = 1.0
ROTATION_DEG = 0

world = bpy.context.scene.world
if world and world.use_nodes:
    for node in world.node_tree.nodes:
        if node.type == 'BACKGROUND':
            node.inputs['Strength'].default_value = STRENGTH
        if node.type == 'MAPPING':
            node.inputs['Rotation'].default_value[2] = math.radians(ROTATION_DEG)

# Rendered viewport, lit by the scene world, so the HDRI is visible
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'RENDERED'
                space.shading.use_scene_world = True
                break
```

### Step 4: Ground plane (only when `ground` is given)

`download_polyhaven_asset(asset_id=<ground>, asset_type="textures", resolution=<resolution>, file_format="jpg")`
returns the name of the material it created. Use that name:

```python
import bpy

MATERIAL = "<material name the download returned>"
GROUND_SIZE = 10

bpy.ops.mesh.primitive_plane_add(size=GROUND_SIZE, location=(0, 0, -0.01))
plane = bpy.context.active_object
plane.name = "Studio_Ground"

mat = bpy.data.materials.get(MATERIAL)
if mat:
    plane.data.materials.append(mat)
```

If the texture download fails, keep the HDRI and say that the ground was skipped.

## Popular Studio HDRIs

- `studio_small_09` — Clean white studio
- `studio_small_08` — Warm studio
- `studio_small_03` — Soft studio lighting
- `photo_studio_loft_hall` — Loft photography studio
- `industrial_sunset_02_puresky` — Golden hour
- `kloppenheim_06_puresky` — Outdoor overcast
- `royal_esplanade` — Grand interior
- `venice_sunset` — Warm sunset
- `snowy_park_01` — Cool daylight
- `meadow_2` — Bright outdoor
