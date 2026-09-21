---
name: blender-threejs-export
description: Export the current Blender scene as a GLB and generate a ready-to-use Three.js HTML viewer with orbit controls, lighting, and auto-rotation. Trigger when asked to export for web, create a Three.js viewer, make a 3D model interactive for a website, or export from Blender for the web.
---

# Blender Three.js Export

Exports the product from Blender as a GLB and writes a standalone HTML file with a Three.js viewer. The viewer includes orbit controls, studio lighting, auto-rotation, and responsive sizing — ready to drop into any website.

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> assembled both the Python it sent and the HTML it wrote from command-line text. The export now goes through the MCP
> server, and the viewer is a fixed template (`assets/viewer.html`) with four named placeholders. See
> `docs/security-review.md`.

## Prerequisites

- **Blender MCP** connected
- A scene loaded in Blender (e.g. after `blender-product-polish`)

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `output` | Folder for the GLB + HTML files | `<JOB_DIR>/web` |
| `name` | File name (without extension): letters, digits, `-` and `_` only | `model` |
| `auto_rotate` | Slow spin to showcase the product | `true` |
| `background` | Background colour, as a hex value like `#111111` | `#111111` |

## Flow

### Step 1: Export the GLB

Export the objects that make up the product, not every mesh in the file. The selection the user had is put back.

```python
import bpy, os

OBJECTS = ["<product object name>", "..."]   # from get_scene_info, or the collection this job built
OUT = "<JOB_DIR>/web/model.glb"

os.makedirs(os.path.dirname(OUT), exist_ok=True)
view_layer = bpy.context.view_layer
was_selected = [o.name for o in bpy.context.selected_objects]
was_active = view_layer.objects.active

bpy.ops.object.select_all(action="DESELECT")
for name in OBJECTS:
    bpy.data.objects[name].select_set(True)

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,          # modifiers are applied in the export only, not on the source mesh
    export_image_format="AUTO",
    export_materials="EXPORT",
    export_texcoords=True,
    export_normals=True,
)

bpy.ops.object.select_all(action="DESELECT")
for name in was_selected:
    if name in bpy.data.objects:
        bpy.data.objects[name].select_set(True)
view_layer.objects.active = was_active

print(f"Exported GLB: {os.path.getsize(OUT) / (1024 * 1024):.1f} MB")
```

### Step 2: Write the viewer

Read `assets/viewer.html` (next to this file), replace the four placeholders, and write the result to
`<output>/<name>.html`:

| Placeholder | Value |
|-------------|-------|
| `{{TITLE}}` | The product's name, as plain text: no `<`, `>`, `&` or quotes |
| `{{BACKGROUND}}` | The hex colour, e.g. `#111111` (appears twice). Nothing but a hex colour |
| `{{GLB_FILE}}` | `./<name>.glb` |
| `{{AUTO_ROTATE}}` | `true` or `false` |

For a single file, `{{GLB_FILE}}` can instead be `data:model/gltf-binary;base64,<the GLB, base64-encoded>`. Do this
only for small models: the page grows by a third of the GLB's size.

## Output

```
<output>/
  model.glb          # GLB export from Blender
  model.html         # Standalone Three.js viewer (CDN imports, no build step)
```

Tell the user that the page loads Three.js 0.170.0 from cdn.jsdelivr.net when it is opened, and that a browser will
not load the GLB from a `file://` page: serve the folder (`python -m http.server`) or use the single-file form.

## Viewer Features

- **Orbit controls** — click and drag to rotate, scroll to zoom, right-click to pan
- **Auto-rotation** — slow spin to showcase the product
- **Studio lighting** — 3-point light setup matching the Blender polish look
- **Glossy override** — every material is made glossy (roughness 0.05, full clearcoat), to match `blender-product-polish`. For a matte product, remove the "Apply glossy material overrides" block from the page
- **Responsive** — fills container, works on mobile
- **Zero dependencies** — uses Three.js from CDN via import maps, no npm/build needed
