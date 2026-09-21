---
name: polyhaven-material-swap
description: Cycle through multiple PolyHaven materials on a product and render each variant. Great for showing color/finish options. Trigger when asked to show material variants, swap textures, create color options, show finish comparisons, or render product in different materials.
---

# PolyHaven Material Swap

Applies multiple PolyHaven PBR textures to the same object one by one and renders each — perfect for showing product finish variants (matte black, glossy white, brushed metal, marble, etc.).

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> sent it Python built from command-line text; it also switched Blender's Cycles device preferences for the whole
> machine. The same steps now go through the MCP server, and the preferences are left alone. See
> `docs/security-review.md`.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `object` | Blender object name | **required** |
| `textures` | PolyHaven texture IDs | **required** (or use a preset) |
| `output` | Folder for the rendered images | `<JOB_DIR>/variants` |
| `preset` | Texture set: metals, woods, stones, fabrics | none |
| `resolution` | Texture resolution: 1k, 2k | `2k` |
| `render_width` / `render_height` | Render size | `1920` x `1080` |
| `samples` | Render samples | `64` |

## Presets

- **metals** — brushed_metal, rusty_metal, painted_metal_02, corrugated_iron
- **woods** — wood_cabinet_worn_long, plywood, bark_brown_02, wood_floor
- **stones** — marble_01, concrete_wall_003, rock_face, gravel_floor_02
- **fabrics** — fabric_pattern_07, leather_red_02, denim_fabric, burlap_01

## Flow

### Step 1: Remember what will change, then set up the render

```python
import bpy

OBJECT = "<object name>"
scene = bpy.context.scene
r = scene.render

# So that step 4 can put everything back
scene["_swap_restore"] = {
    "engine": r.engine, "samples": scene.cycles.samples, "denoise": scene.cycles.use_denoising,
    "res_x": r.resolution_x, "res_y": r.resolution_y, "format": r.image_settings.file_format,
    "filepath": r.filepath,
}
obj = bpy.data.objects.get(OBJECT)
if obj and obj.data.materials and obj.data.materials[0]:
    scene["_original_mat"] = obj.data.materials[0].name

r.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
r.resolution_x, r.resolution_y = 1920, 1080
r.image_settings.file_format = 'PNG'

# A camera only if the scene has none
if scene.camera is None:
    import mathutils
    bpy.ops.object.camera_add(location=(2.5, -2.5, 1.5))
    cam = bpy.context.active_object
    cam.name = 'Variants_Camera'
    scene.camera = cam
    direction = mathutils.Vector((0, 0, 0)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
```

### Step 2: For each texture — download, apply, render

`download_polyhaven_asset(asset_id=<texture>, asset_type="textures", resolution=<resolution>, file_format="jpg")`
returns the material name. If a download fails, skip that texture and say so.

```python
import bpy

OBJECT = "<object name>"
MATERIAL = "<material name the download returned>"
OUT = "<JOB_DIR>/variants/<texture id>.png"

obj = bpy.data.objects.get(OBJECT)
mat = bpy.data.materials.get(MATERIAL)
if obj and mat:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    bpy.context.scene.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
```

### Step 3: Look at every render

Read each image before reporting: a variant that rendered black or untextured is a failed variant.

### Step 4: Put the scene back

```python
import bpy

OBJECT = "<object name>"
scene = bpy.context.scene
obj = bpy.data.objects.get(OBJECT)

orig_name = scene.get("_original_mat")
if obj and orig_name:
    mat = bpy.data.materials.get(orig_name)
    if mat and obj.data.materials:
        obj.data.materials[0] = mat

saved = scene.get("_swap_restore")
if saved:
    r = scene.render
    r.engine = saved["engine"]
    scene.cycles.samples = saved["samples"]
    scene.cycles.use_denoising = saved["denoise"]
    r.resolution_x, r.resolution_y = saved["res_x"], saved["res_y"]
    r.image_settings.file_format = saved["format"]
    r.filepath = saved["filepath"]
for key in ("_swap_restore", "_original_mat"):
    if key in scene:
        del scene[key]
```
