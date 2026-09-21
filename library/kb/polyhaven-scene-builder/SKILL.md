---
name: polyhaven-scene-builder
description: Build complete product scenes using PolyHaven assets — HDRI environment, textured ground/pedestal, and optional props from the 3D model library. Trigger when asked to build a product scene, create a showcase setup, add a pedestal, or compose a product shot.
---

# PolyHaven Scene Builder

Builds a full product photography scene around your 3D model: HDRI environment, textured ground plane or pedestal, and optional prop models from PolyHaven's free library.

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> sent it Python built from command-line text. The same steps now go through the MCP server, where each one is visible
> and asks for permission. See `docs/security-review.md`.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `hdri` | PolyHaven HDRI asset ID | `studio_small_09` |
| `ground` | PolyHaven texture for the ground | none |
| `pedestal` | Add a cylindrical pedestal under the product | `false` |
| `pedestal_texture` | Texture for the pedestal | same as ground |
| `props` | PolyHaven model IDs to add | none |
| `resolution` | Asset resolution: 1k, 2k, 4k | `2k` |
| `preset` | Quick preset: showroom, outdoor, minimal, dramatic | none |

## Presets

| Preset | HDRI | Ground | Pedestal |
|--------|------|--------|----------|
| **showroom** | `studio_small_09` | `marble_01` | yes |
| **outdoor** | `kloppenheim_06_puresky` | `concrete_wall_003` | no |
| **minimal** | `studio_small_03` | none (floating product) | no |
| **dramatic** | `industrial_sunset_02_puresky` | `concrete_floor_02` | yes |

## Flow

### Step 1: HDRI environment

The add-on's HDRI download rebuilds the first World in the file in place. If the scene has a World this job did not
make, copy it first (`keep = scene.world.copy(); keep.name = "KEEP-" + scene.world.name; keep.use_fake_user = True`).

`download_polyhaven_asset(asset_id=<hdri>, asset_type="hdris", resolution=<resolution>, file_format="hdr")`

Then switch the viewport to rendered shading with the scene world, so the result can be judged:

```python
import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'RENDERED'
                space.shading.use_scene_world = True
                break
```

### Step 2: Textured ground (only when `ground` is given)

`download_polyhaven_asset(asset_id=<ground>, asset_type="textures", resolution=<resolution>, file_format="jpg")`
returns the name of the material it created.

```python
import bpy

MATERIAL = "<material name the download returned>"

bpy.ops.mesh.primitive_plane_add(size=15, location=(0, 0, -0.01))
plane = bpy.context.active_object
plane.name = "Scene_Ground"
mat = bpy.data.materials.get(MATERIAL)
if mat:
    plane.data.materials.append(mat)
    # Scale UVs for better tiling
    for node in mat.node_tree.nodes:
        if node.type == 'MAPPING':
            node.inputs['Scale'].default_value = (3, 3, 3)
```

### Step 3: Pedestal (only when `pedestal` is set)

Name the product object. Do not guess it from "the first mesh in the file": ask `get_scene_info`, or the user.

```python
import bpy

PRODUCT = "<name of the product object>"
PEDESTAL_MATERIAL = "<material name from step 2, or empty>"

product = bpy.data.objects[PRODUCT]
dims = product.dimensions
radius = max(dims.x, dims.y) * 0.7
bpy.ops.mesh.primitive_cylinder_add(
    radius=radius,
    depth=0.08,
    location=(product.location.x, product.location.y, product.location.z - dims.z / 2 - 0.04)
)
ped = bpy.context.active_object
ped.name = "Pedestal"
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.get(PEDESTAL_MATERIAL) if PEDESTAL_MATERIAL else None
if mat is None:
    # A simple dark glossy material
    mat = bpy.data.materials.new("Pedestal_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    bsdf.inputs["Roughness"].default_value = 0.1
    bsdf.inputs["Metallic"].default_value = 0.3
ped.data.materials.append(mat)
print(f"Pedestal added: radius={radius:.2f}")
```

### Step 4: Props (only when `props` is given)

For each model ID:
`download_polyhaven_asset(asset_id=<prop>, asset_type="models", resolution=<resolution>, file_format="gltf")`.
The result lists the objects it imported; place them beside the product, never on top of it. If one fails, say so and
carry on with the rest.
