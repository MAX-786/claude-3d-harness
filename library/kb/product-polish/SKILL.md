---
name: blender-product-polish
description: Import a 3D model (GLB/GLTF) into Blender and apply a sleek, glossy product-shot finish with studio lighting. Trigger when asked to polish a 3D model, make a Meshy AI model look shiny, apply product lighting in Blender, or prepare a 3D asset for product shots.
---

# Blender Product Polish

Takes a raw 3D model file (typically exported from Meshy AI) and transforms it into a polished, product-shot-ready scene in Blender.

> Adapted for claude-3d-harness. The original ran a bundled Node script that opened Blender's add-on socket itself and
> sent it Python built from command-line text. By default it emptied the scene, and it rewrote every material and
> deleted every light in the file, not only the imported model's. The same finish is now applied through the MCP
> server, to the imported model only, and nothing already in the scene is removed. See `docs/security-review.md`.

## Prerequisites

- **Blender MCP** connected
- A `.glb` or `.gltf` file to import (absolute path)

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `file` | Path to the GLB/GLTF file to import | **required** |
| `preset` | Lighting preset: `studio`, `dramatic`, `soft` | `studio` |
| `roughness` | Surface roughness (0 = mirror, 1 = matte) | `0.02` |
| `coat` | Clearcoat weight (0-1) | `1.0` |
| `transmission` | Glass transmission (0-1) | `0.05` |

## Lighting Presets

| Preset | Key | Fill | Rim | Bounce | Look |
|--------|-----|------|-----|--------|------|
| **studio** (default) | 350 W | 250 W | 250 W | 100 W | Balanced 4-point setup. Clean product photography |
| **dramatic** | 500 W | 80 W | 400 W | 50 W | Strong key + rim, minimal fill. High contrast, moody |
| **soft** | 200 W | 200 W | 150 W | 150 W | Even lighting from all sides. Minimal shadows, airy |

## Flow

### Step 1: Import the model and remember what came in

```python
import bpy

FILE = "<absolute path to the .glb or .gltf>"

before = {o.name for o in bpy.data.objects}
bpy.ops.import_scene.gltf(filepath=FILE)
imported = [o for o in bpy.data.objects if o.name not in before]

col = bpy.data.collections.new("Polish_Import")
bpy.context.scene.collection.children.link(col)
for o in imported:
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
print(f"Imported {len([o for o in imported if o.type == 'MESH'])} mesh object(s) into {col.name}")
```

### Step 2: Glossy finish, on the imported model's materials only

Meshy AI exports often include normal maps and roughness textures that look pixelated/dotty under strong lighting.
This disconnects those and uses flat values instead.

```python
import bpy

ROUGHNESS, COAT, TRANSMISSION = 0.02, 1.0, 0.05

col = bpy.data.collections["Polish_Import"]
mats = {s.material for o in col.objects if o.type == 'MESH' for s in o.material_slots if s.material}

for mat in mats:
    if not mat.use_nodes:
        continue
    nodes, links = mat.node_tree.nodes, mat.node_tree.links

    # Remove normal map / roughness texture links (cause dotty reflections from Meshy exports)
    for link in [l for l in links if l.to_socket.name in ["Normal", "Roughness", "Metallic"]]:
        links.remove(link)
    for n in [n for n in nodes if n.type in ["SEPARATE_COLOR", "NORMAL_MAP"]]:
        nodes.remove(n)
    for n in [n for n in nodes if n.type == "TEX_IMAGE"]:
        if not any(link for out in n.outputs for link in out.links):
            nodes.remove(n)

    # Glass-like BSDF settings
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            node.inputs["Roughness"].default_value = ROUGHNESS
            node.inputs["Specular IOR Level"].default_value = 1.0
            node.inputs["Coat Weight"].default_value = COAT
            node.inputs["Coat Roughness"].default_value = 0.0
            node.inputs["Metallic"].default_value = 0.1
            node.inputs["IOR"].default_value = 1.8
            node.inputs["Transmission Weight"].default_value = TRANSMISSION

print(f"Polished {len(mats)} material(s)")
```

### Step 3: 4-point studio lighting

If the scene already has lights, ask before adding more: these are added beside them, never in their place.

```python
import bpy, math

KEY, FILL, RIM, BOUNCE = 350, 250, 250, 100   # the 'studio' preset; see the table above

col = bpy.data.collections["Polish_Import"]

def area_light(name, energy, size, color, location, rotation_deg):
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy, data.size, data.color = energy, size, color
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.location = location
    obj.rotation_euler = tuple(math.radians(a) for a in rotation_deg)
    return obj

area_light("Polish_Key",    KEY,    3, (1.0, 0.95, 0.9), (2, -2, 3),    (45, 0, 45))
area_light("Polish_Fill",   FILL,   4, (0.9, 0.95, 1.0), (-2.5, -1, 2), (50, 0, -45))
area_light("Polish_Rim",    RIM,    2, (1.0, 1.0, 1.0),  (0, 2, 2.5),   (130, 0, 0))
area_light("Polish_Bounce", BOUNCE, 5, (1.0, 1.0, 1.0),  (0, 0, -1),    (180, 0, 0))
```

Only in a scene this job built from empty, dim the world so the lights do the work:

```python
import bpy
world = bpy.context.scene.world
bg = world.node_tree.nodes.get("Background") if world and world.use_nodes else None
if bg:
    bg.inputs["Strength"].default_value = 0.3
    bg.inputs["Color"].default_value = (0.15, 0.15, 0.18, 1.0)
```

### Step 4: Viewport

EEVEE with ray tracing gives smooth real-time reflections (no pixelation while orbiting). This changes the scene's
render engine: say so in the report, and skip it if the user has a Cycles setup they render with.

```python
import bpy

bpy.context.scene.render.engine = "BLENDER_EEVEE"
try:
    bpy.context.scene.eevee.use_raytracing = True
except Exception:
    pass

# Frame the imported model
bpy.ops.object.select_all(action="DESELECT")
for o in bpy.data.collections["Polish_Import"].objects:
    o.select_set(True)
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = "RENDERED"
                break
        for region in area.regions:
            if region.type == "WINDOW":
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_selected()
                break
        break
```
