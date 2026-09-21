---
name: polyhaven-texture-apply
description: Apply realistic PBR textures from PolyHaven to any Blender object. Supports metals, wood, concrete, fabric, and more. Trigger when asked to texture an object, apply a material from PolyHaven, make something look like metal/wood/marble, or change object surface.
---

# PolyHaven Texture Apply

Downloads a full PBR texture set (diffuse, roughness, normal, displacement) from PolyHaven and applies it to a specific object in the Blender scene.

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> sent it Python built from command-line text. The same steps now go through the MCP server, where each one is visible
> and asks for permission. See `docs/security-review.md`.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `object` | Blender object name to apply the texture to | **required** |
| `texture` | PolyHaven texture asset ID | **required** |
| `resolution` | Texture resolution: 1k, 2k, 4k | `2k` |
| `scale` | UV mapping scale | `1.0` |

## Flow

### Step 1: Find a texture (when the user named a look, not an ID)

`search_polyhaven_assets(asset_type="textures", categories=<keyword>)` lists IDs with their categories.

### Step 2: Download the PBR set

`download_polyhaven_asset(asset_id=<texture>, asset_type="textures", resolution=<resolution>, file_format="jpg")`
returns the name of the material it created and the maps it found.

### Step 3: Apply it

`set_texture(object_name=<object>, texture_id=<texture>)`

If that fails, assign the material by hand. This replaces the material in the object's first slot, which is what was
asked for; the material that was there stays in the file.

```python
import bpy

OBJECT = "<object name>"
MATERIAL = "<material name the download returned>"
SCALE = 1.0

obj = bpy.data.objects.get(OBJECT)
mat = bpy.data.materials.get(MATERIAL)
if obj and mat:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    # Adjust UV scale
    for node in mat.node_tree.nodes:
        if node.type == 'MAPPING':
            node.inputs['Scale'].default_value = (SCALE, SCALE, SCALE)
    print(f"Applied {mat.name} to {obj.name}")
else:
    print(f"Error: obj={'found' if obj else 'missing'}, mat={'found' if mat else 'missing'}")
```

## Popular Textures

- `brushed_metal` — Brushed aluminum/steel
- `carbon_fiber` — Carbon fiber weave
- `marble_01` — White marble
- `wood_cabinet_worn_long` — Aged wood
- `concrete_wall_003` — Raw concrete
- `leather_red_02` — Red leather
- `fabric_pattern_07` — Woven fabric
