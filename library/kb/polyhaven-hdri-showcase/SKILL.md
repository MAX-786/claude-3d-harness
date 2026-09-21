---
name: polyhaven-hdri-showcase
description: Render the same product across multiple HDRI environments and output a comparison grid. Trigger when asked to compare lighting setups, test different environments, show product in multiple settings, or create an HDRI comparison.
---

# PolyHaven HDRI Showcase

Renders your product across multiple PolyHaven HDRI environments and saves each as an image — perfect for picking the best lighting for your product shots or creating a showcase grid.

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> sent it Python built from command-line text; it switched Blender's Cycles device preferences for the whole machine
> and left the scene lit by whichever HDRI came last. The same steps now go through the MCP server, the preferences
> are left alone, and the scene's own World is given back at the end. See `docs/security-review.md`.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `output` | Folder for the rendered images | `<JOB_DIR>/hdri` |
| `hdris` | HDRI IDs to compare | the default set of 6 |
| `preset` | HDRI set: studios, outdoor, dramatic, all | none |
| `resolution` | HDRI resolution: 1k, 2k | `1k` |
| `render_width` / `render_height` | Render size | `1920` x `1080` |
| `samples` | Render samples | `64` |

## HDRI sets

- **default** — studio_small_09, studio_small_08, royal_esplanade, kloppenheim_06_puresky, industrial_sunset_02_puresky, venice_sunset
- **studios** — studio_small_09, studio_small_08, studio_small_03, photo_studio_loft_hall
- **outdoor** — kloppenheim_06_puresky, meadow_2, snowy_park_01, venice_sunset
- **dramatic** — industrial_sunset_02_puresky, royal_esplanade, abandoned_tiled_room, moonless_golf
- **all** — the three sets above

## Flow

### Step 1: Keep the World, remember the render settings, set up the render

The add-on's HDRI download rebuilds the first World in the file in place, once per HDRI. Copy the scene's World first.

```python
import bpy

scene = bpy.context.scene
r = scene.render

if scene.world:
    keep = scene.world.copy()
    keep.name = "KEEP-" + scene.world.name
    keep.use_fake_user = True
    scene["_showcase_world"] = keep.name

scene["_showcase_restore"] = {
    "engine": r.engine, "samples": scene.cycles.samples, "denoise": scene.cycles.use_denoising,
    "res_x": r.resolution_x, "res_y": r.resolution_y, "format": r.image_settings.file_format,
    "filepath": r.filepath,
}

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
    cam.name = 'Showcase_Camera'
    scene.camera = cam
    direction = mathutils.Vector((0, 0, 0)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
```

### Step 2: For each HDRI — download, render

`download_polyhaven_asset(asset_id=<hdri>, asset_type="hdris", resolution=<resolution>, file_format="hdr")`
applies it to the scene. If a download fails, skip that HDRI and say so.

```python
import bpy
bpy.context.scene.render.filepath = "<JOB_DIR>/hdri/<hdri id>.png"
bpy.ops.render.render(write_still=True)
```

### Step 3: Look at every render

Read each image, then tell the user which environments suit the product and why. If they asked for a grid, lay the
images out in one; the renders alone are not a comparison.

### Step 4: Give the scene its World and settings back

Unless the user picked one of the HDRIs to keep:

```python
import bpy

scene = bpy.context.scene
name = scene.get("_showcase_world")
if name and name in bpy.data.worlds:
    scene.world = bpy.data.worlds[name]

saved = scene.get("_showcase_restore")
if saved:
    r = scene.render
    r.engine = saved["engine"]
    scene.cycles.samples = saved["samples"]
    scene.cycles.use_denoising = saved["denoise"]
    r.resolution_x, r.resolution_y = saved["res_x"], saved["res_y"]
    r.image_settings.file_format = saved["format"]
    r.filepath = saved["filepath"]
for key in ("_showcase_restore", "_showcase_world"):
    if key in scene:
        del scene[key]
```
