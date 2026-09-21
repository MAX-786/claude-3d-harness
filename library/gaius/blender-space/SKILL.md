---
description: >
  Skill di geometria 3D e orientamento spaziale per Blender. Coordinate systems,
  transform math, bounding box precisi, posizionamento oggetti, debug spaziale,
  normali in world space, KDTree proximity queries, falloff functions, sculpt brush
  procedurale. Usa questa skill ogni volta che devi: posizionare oggetti con
  precisione, calcolare distanze/angoli, capire dove sono i vertici nel mondo,
  gestire parent-child, orientare la camera, lavorare con rotazioni, fare sculpting
  o deformazioni programmatiche con brush influence.
allowed-tools:
  - Bash
  - PowerShell
  - Read
  - Write
  - mcp__Blender__execute_blender_code
---

# Skill: Blender 3D Space & Geometry

Sei un esperto di geometria 3D in Blender. Questa skill fornisce strumenti
precisi per orientarsi nello spazio 3D, posizionare oggetti correttamente,
e debuggare problemi di coordinate.

---

## IL PRINCIPIO PIÙ IMPORTANTE

> **`obj.location` ≠ posizione dei vertici nel mondo.**
>
> Blender ha due sistemi separati:
> - **Object origin**: `obj.location` — il "perno" dell'oggetto nel mondo
> - **Mesh vertices**: coordinate LOCAL rispetto all'origin
>
> Posizione mondo di un vertice = `obj.matrix_world @ vertex.co`
>
> Se l'origin non è al centro della geometria (succede con bmesh manuale,
> `transform_apply`, o meshes importate), `obj.location` è fuorviante.

### Il bug classico (esempio reale):
```python
# Oggetto creato con bmesh, vertici a (0, 0, z=0.285) in local space
# obj.location = (0, 0, 0)  ← origin all'origine
# ERRORE: pensare che obj.location.z=0.1 metta l'oggetto a z=0.1
#         in realtà l'oggetto è a z = 0 + 0.285 = 0.285 nel mondo!

# CORRETTO: misura prima, poi calcola
offset = get_world_center(obj).z - obj.location.z
# Poi: obj.location.z = target_world_z - offset
```

---

## FUNZIONI DI DEBUG SPAZIALE

```python
def blender(code, timeout=30):
    import urllib.request, json
    data = json.dumps({"code": code, "timeout": timeout}).encode()
    req  = urllib.request.Request("http://localhost:7234/execute", data=data,
                                  headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout+10).read())
    if "error" in r: print("ERR:", r["error"][:500]); return None
    return r.get("ok")

# ── MISURA POSIZIONE REALE (WORLD SPACE) ────────────────────────────────────
MEASURE = """
import bpy

def world_bounds(obj):
    '''Bounding box reale in world space. USA SEMPRE QUESTA.'''
    verts_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not verts_world:
        # Fallback per oggetti senza vertices (curve, empty, light)
        loc = obj.matrix_world.translation
        return {'center': list(loc), 'min': list(loc), 'max': list(loc), 'size': [0,0,0]}
    xs = [v.x for v in verts_world]
    ys = [v.y for v in verts_world]
    zs = [v.z for v in verts_world]
    return {
        'min':    [min(xs), min(ys), min(zs)],
        'max':    [max(xs), max(ys), max(zs)],
        'center': [(min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2],
        'size':   [max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)],
        'origin_offset': [           # quanto l'origin è spostato dal centro geometria
            obj.location.x - (min(xs)+max(xs))/2,
            obj.location.y - (min(ys)+max(ys))/2,
            obj.location.z - (min(zs)+max(zs))/2,
        ]
    }

# Esempio: misura tutti gli oggetti mesh nella scena
info = {}
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        b = world_bounds(obj)
        info[obj.name] = {
            'origin': [round(obj.location.x,3), round(obj.location.y,3), round(obj.location.z,3)],
            'world_center': [round(v,3) for v in b['center']],
            'world_zmin': round(b['min'][2],3),
            'world_zmax': round(b['max'][2],3),
            'size': [round(v,3) for v in b['size']],
            'origin_offset_z': round(b['origin_offset'][2],3)  # chiave! se ≠0 c'è mismatch
        }
result = info
"""
```

---

## SISTEMI DI COORDINATE

### Gerarchia dei sistemi in Blender

```
WORLD SPACE          ← sistema assoluto, quello che vediamo nel render
    │
    └── LOCAL SPACE   ← relativo all'object origin (obj.location + rotation)
            │
            └── UV SPACE     ← 2D per textures (u,v in [0,1])
            └── CAMERA SPACE ← relativo alla camera (z = depth)
            └── SCREEN SPACE ← pixel sullo schermo
```

### Conversioni fondamentali

```python
import bpy
from mathutils import Vector, Matrix

# LOCAL → WORLD
def local_to_world(obj, local_point):
    return obj.matrix_world @ Vector(local_point)

# WORLD → LOCAL
def world_to_local(obj, world_point):
    return obj.matrix_world.inverted() @ Vector(world_point)

# WORLD → CAMERA SPACE
def world_to_camera(scene, camera, world_point):
    from bpy_extras.object_utils import world_to_camera_space
    return world_to_camera_space(scene, camera, Vector(world_point))
    # restituisce (x, y, z) dove x,y ∈ [0,1] = posizione sullo schermo
    # z = profondità (distanza dalla camera)

# Esempi
obj    = bpy.data.objects["Apple"]
cam    = bpy.data.objects["Camera"]
scene  = bpy.context.scene

# Dove sono i vertici del oggetto nel mondo?
world_verts = [obj.matrix_world @ v.co for v in obj.data.vertices]

# Dove appare un punto del mondo sullo schermo?
screen_pos = world_to_camera(scene, cam, (0, 0, 0.2))
print(f"Il punto (0,0,0.2) appare a {screen_pos.x:.2f}, {screen_pos.y:.2f} dello schermo")
```

---

## POSIZIONAMENTO PRECISO

### Pattern corretto per posizionare un oggetto

```python
def place_object_world(obj, target_world_pos, anchor='center'):
    """
    Posiziona obj in modo che la sua geometria sia centrata (o allineata)
    a target_world_pos nel mondo, indipendentemente dall'origin offset.

    anchor:
      'center' → centro geometria a target_world_pos
      'bottom' → base geometria a target_world_pos (z del vertice più basso)
      'top'    → cima geometria a target_world_pos
    """
    # Calcola bounds attuali in world space
    verts_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    zs = [v.z for v in verts_world]
    xs = [v.x for v in verts_world]
    ys = [v.y for v in verts_world]

    # Centro geometrico in world space
    geo_center = Vector([(min(xs)+max(xs))/2,
                         (min(ys)+max(ys))/2,
                         (min(zs)+max(zs))/2])

    # Offset tra origin e geo center (in world space)
    origin_to_geo = geo_center - obj.matrix_world.translation

    target = Vector(target_world_pos)

    if anchor == 'center':
        obj.location = target - origin_to_geo
    elif anchor == 'bottom':
        bottom_offset = geo_center.z - min(zs)   # distanza centro→base
        obj.location.z = target.z + bottom_offset - origin_to_geo.z
        obj.location.x = target.x - origin_to_geo.x
        obj.location.y = target.y - origin_to_geo.y
    elif anchor == 'top':
        top_offset = max(zs) - geo_center.z      # distanza centro→cima
        obj.location.z = target.z - top_offset - origin_to_geo.z
        obj.location.x = target.x - origin_to_geo.x
        obj.location.y = target.y - origin_to_geo.y

# Esempio: metti la mela con la base a z=0.05
place_object_world(apple, (−0.08, 0.05, 0.05), anchor='bottom')
```

### Stack verticale di oggetti

```python
def stack_on_top(base_obj, new_obj, gap=0.002):
    """Posiziona new_obj sopra base_obj con gap di separazione."""
    # Top del base in world space
    base_verts = [base_obj.matrix_world @ v.co for v in base_obj.data.vertices]
    base_top   = max(v.z for v in base_verts)

    # Bottom del nuovo oggetto
    new_verts  = [new_obj.matrix_world @ v.co for v in new_obj.data.vertices]
    new_bot    = min(v.z for v in new_verts)

    # Sposta in modo che il bottom sia appena sopra il base_top
    delta_z = (base_top + gap) - new_bot
    new_obj.location.z += delta_z

# Esempio: impila pera sopra mela
stack_on_top(apple, pear, gap=0.005)
```

### Allineamento orizzontale

```python
def align_objects(objects, axis='x', mode='center'):
    """
    Allinea oggetti lungo un asse.
    axis: 'x', 'y', 'z'
    mode: 'center' (centra i centri), 'min' (allinea basi), 'max' (allinea cime)
    """
    idx = {'x':0, 'y':1, 'z':2}[axis]
    targets = []
    for obj in objects:
        verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        vals  = [getattr(v, axis) for v in verts]
        if mode == 'center': targets.append((min(vals)+max(vals))/2)
        elif mode == 'min':  targets.append(min(vals))
        elif mode == 'max':  targets.append(max(vals))

    avg = sum(targets) / len(targets)

    for obj, t in zip(objects, targets):
        diff = avg - t
        if axis == 'x': obj.location.x += diff
        elif axis == 'y': obj.location.y += diff
        elif axis == 'z': obj.location.z += diff
```

---

## ROTAZIONI

### Euler vs Quaternion

```python
import math
from mathutils import Euler, Quaternion, Matrix

# ── EULER ANGLES (rotation_euler) ─────────────────────────────
# Blender usa XYZ Euler di default
# rotation_euler = (rx, ry, rz) in RADIANTI

obj.rotation_euler = (math.radians(45), 0, math.radians(30))
#                      ↑ tilt avanti     ↑ no roll    ↑ girata

# ATTENZIONE: ordine degli assi conta!
# 'XYZ' = prima ruota X, poi Y nel nuovo sistema, poi Z
obj.rotation_mode = 'XYZ'   # default
obj.rotation_mode = 'ZYX'   # per alcuni casi (aeronautica)
obj.rotation_mode = 'QUATERNION'  # senza gimbal lock

# ── QUATERNION ─────────────────────────────────────────────────
# Per rotazioni complesse senza gimbal lock
obj.rotation_mode = 'QUATERNION'
obj.rotation_quaternion = Quaternion((0, 0, 1), math.radians(45))
#                                     ↑ asse Z   ↑ angolo

# ── MATRIX ROTATION ────────────────────────────────────────────
# Ruota intorno a un asse arbitrario
axis   = Vector((1, 0.5, 0)).normalized()   # asse diagonale
angle  = math.radians(30)
rot    = Matrix.Rotation(angle, 4, axis)    # matrice 4x4
obj.matrix_world = rot @ obj.matrix_world   # applica

# ── LOOK-AT (punta verso un punto) ─────────────────────────────
def point_at(obj, target_world, track_axis='-Z', up_axis='Y'):
    """Orienta obj verso target nel mondo."""
    direction = Vector(target_world) - obj.location
    rot_quat  = direction.to_track_quat(track_axis, up_axis)
    obj.rotation_euler = rot_quat.to_euler()

# Esempio: punta la camera verso il cestino
point_at(camera, (0, 0, 0.2), track_axis='-Z', up_axis='Y')
```

### Angoli tra oggetti

```python
def angle_between_objects(obj_a, obj_b):
    """Angolo (in gradi) che obj_a deve ruotare per puntare a obj_b."""
    direction = (obj_b.location - obj_a.location).normalized()
    forward   = Vector((0, -1, 0))  # forward di default in Blender
    return math.degrees(forward.angle(direction))

def azimuth_elevation(observer, target):
    """
    Restituisce (azimuth, elevation) in gradi.
    Azimuth = angolo orizzontale (0=Nord/+Y, 90=Est/+X)
    Elevation = angolo verticale (0=orizzontale, 90=zenith)
    """
    d = Vector(target) - Vector(observer)
    horiz = Vector((d.x, d.y, 0)).length
    elevation = math.degrees(math.atan2(d.z, horiz))
    azimuth   = math.degrees(math.atan2(d.x, d.y))
    return azimuth, elevation
```

---

## BOUNDING BOX E DISTANZE

```python
# ── DISTANZA TRA OGGETTI ────────────────────────────────────────
def distance_between(obj_a, obj_b):
    """Distanza tra i centri geometrici nel mondo."""
    ca = sum([obj_a.matrix_world @ v.co for v in obj_a.data.vertices],
             Vector()) / len(obj_a.data.vertices)
    cb = sum([obj_b.matrix_world @ v.co for v in obj_b.data.vertices],
             Vector()) / len(obj_b.data.vertices)
    return (ca - cb).length

def surface_distance(obj_a, obj_b):
    """Distanza approssimata tra superfici (non centri) lungo Z."""
    va = [obj_a.matrix_world @ v.co for v in obj_a.data.vertices]
    vb = [obj_b.matrix_world @ v.co for v in obj_b.data.vertices]
    top_a  = max(v.z for v in va)
    bot_b  = min(v.z for v in vb)
    return bot_b - top_a   # positivo = gap, negativo = overlap

# ── OVERLAP CHECK ───────────────────────────────────────────────
def objects_overlap_z(obj_a, obj_b):
    """Controlla se i bounding box si sovrappongono in Z."""
    va = [obj_a.matrix_world @ v.co for v in obj_a.data.vertices]
    vb = [obj_b.matrix_world @ v.co for v in obj_b.data.vertices]
    a_min, a_max = min(v.z for v in va), max(v.z for v in va)
    b_min, b_max = min(v.z for v in vb), max(v.z for v in vb)
    return a_min < b_max and b_min < a_max

# ── SCENE BOUNDS ─────────────────────────────────────────────────
def scene_bounds(exclude_names=None):
    """Bounding box di tutta la scena."""
    exclude_names = exclude_names or []
    all_verts = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name not in exclude_names:
            all_verts.extend([obj.matrix_world @ v.co for v in obj.data.vertices])
    if not all_verts: return None
    return {
        'min':  Vector((min(v.x for v in all_verts), min(v.y for v in all_verts), min(v.z for v in all_verts))),
        'max':  Vector((max(v.x for v in all_verts), max(v.y for v in all_verts), max(v.z for v in all_verts))),
        'size': Vector((max(v.x for v in all_verts) - min(v.x for v in all_verts),
                        max(v.y for v in all_verts) - min(v.y for v in all_verts),
                        max(v.z for v in all_verts) - min(v.z for v in all_verts))),
    }
```

---

## ORIGINS E PIVOT

```python
# ── SET ORIGIN AL CENTRO DELLA GEOMETRIA ───────────────────────
def recenter_origin(obj):
    """Sposta l'origin al centro geometrico. Risolve il bug apple."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    # Dopo questo: obj.location = world center della geometria ✓

# ── SET ORIGIN ALLA BASE ─────────────────────────────────────────
def origin_to_bottom(obj):
    """Sposta l'origin alla base dell'oggetto (utile per posizionamento su piano)."""
    bpy.context.view_layer.objects.active = obj
    # Modo manuale: calcola punto più basso in world, poi impostal come cursore
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    bottom_z = min(v.z for v in verts)
    geo_center_x = (max(v.x for v in verts) + min(v.x for v in verts)) / 2
    geo_center_y = (max(v.y for v in verts) + min(v.y for v in verts)) / 2
    bpy.context.scene.cursor.location = (geo_center_x, geo_center_y, bottom_z)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # Ora obj.location.z = z della base dell'oggetto nel mondo ✓

# ── APPLICA TUTTI I TRANSFORM ───────────────────────────────────
def apply_all_transforms(obj):
    """
    Bake location + rotation + scale nei vertici.
    DOPO: obj.location=(0,0,0), obj.rotation=(0,0,0), obj.scale=(1,1,1)
    e i vertici sono in world space come local space.
    ATTENZIONE: rompe i riferimenti parent-child.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

---

## CAMERA E PROIEZIONE

```python
# ── DISTANZA ESATTA CAMERA → PUNTO ──────────────────────────────
def cam_focus_distance(cam, world_point):
    """Calcola la distanza esatta dalla camera a un punto nel mondo."""
    cam_loc = cam.matrix_world.translation
    return (Vector(world_point) - cam_loc).length

# ── FOV E CONO VISIVO ───────────────────────────────────────────
def camera_fov(cam, axis='h'):
    """
    FOV della camera in gradi.
    axis='h' → orizzontale, 'v' → verticale, 'd' → diagonale
    """
    lens    = cam.data.lens
    sensor  = cam.data.sensor_width if axis == 'h' else cam.data.sensor_height
    return math.degrees(2 * math.atan(sensor / (2 * lens)))

# ── QUANTO È GRANDE UN OGGETTO NEL FRAME? ───────────────────────
def object_screen_coverage(scene, cam, obj):
    """
    Stima quanta parte dello schermo occupa l'oggetto.
    Ritorna (width_pct, height_pct) in percentuale [0,1].
    """
    from bpy_extras.object_utils import world_to_camera_space
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    # Sample ogni N vertici per velocità
    sample = verts[::max(1, len(verts)//50)]
    screen_pts = [world_to_camera_space(scene, cam, v) for v in sample]
    # Filtra vertici davanti alla camera (z positivo = dietro)
    visible = [p for p in screen_pts if p.z > 0]
    if not visible: return 0, 0
    xs = [p.x for p in visible]; ys = [p.y for p in visible]
    return max(xs)-min(xs), max(ys)-min(ys)

# ── AUTO-FRAME: posiziona camera per inquadrare tutti gli oggetti ──
def auto_frame_camera(cam, objects, margin=1.3):
    """
    Posiziona la camera per inquadrare tutti gli oggetti con margin.
    margin > 1 = più spazio intorno.
    """
    # Bounding box di tutti gli oggetti
    all_verts = []
    for obj in objects:
        all_verts.extend([obj.matrix_world @ v.co for v in obj.data.vertices])
    if not all_verts: return

    center = Vector([
        (max(v.x for v in all_verts) + min(v.x for v in all_verts)) / 2,
        (max(v.y for v in all_verts) + min(v.y for v in all_verts)) / 2,
        (max(v.z for v in all_verts) + min(v.z for v in all_verts)) / 2,
    ])
    radius = max((Vector(v) - center).length for v in all_verts) * margin

    # Distanza necessaria perché radius sia nel frame
    fov_rad = math.radians(camera_fov(cam, 'v') / 2)
    dist    = radius / math.tan(fov_rad) if fov_rad > 0 else radius * 5

    # Mantieni direzione corrente, scala la distanza
    direction = (cam.location - center).normalized()
    cam.location = center + direction * dist
    cam.data.dof.focus_distance = dist
```

---

## PARENT-CHILD E MATRIX

```python
# ── PARENT SENZA SPOSTARE L'OGGETTO ─────────────────────────────
def parent_keep_transform(child, parent):
    """
    Aggiunge child come figlio di parent SENZA spostarlo nel mondo.
    Fondamentale: child mantiene la sua posizione visiva.
    """
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    # matrix_parent_inverse compensa la trasformazione del parent

# ── WORLD MATRIX: capire tutto in un colpo ──────────────────────
def explain_matrix(obj):
    """Spiega la matrix_world di un oggetto."""
    m = obj.matrix_world
    loc, rot, scale = m.decompose()
    return {
        'world_position': list(loc),
        'world_rotation_euler_deg': [math.degrees(a) for a in rot.to_euler()],
        'world_scale': list(scale),
    }

# ── MATRIX COMPOSIZIONE ──────────────────────────────────────────
# matrix_world = matrix_parent_world @ matrix_local
# matrix_local = matrix_basis @ matrix_parent_inverse
#
# Per spostare un figlio nel mondo senza toccarne il local:
child.matrix_world = Matrix.Translation((new_x, new_y, new_z)) @ \
                     Matrix.Rotation(angle, 4, 'Z') @ \
                     child.matrix_world
```

---

## PATTERN DI LAVORO CONSIGLIATO

### Workflow sicuro per posizionamento

```python
# STEP 1: Misura SEMPRE prima di spostare
def safe_place(obj, target_x, target_y, target_z, anchor='center'):
    """Posiziona obj con correzione automatica dell'origin offset."""
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not verts: return

    xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
    cx = (min(xs)+max(xs))/2;  cy = (min(ys)+max(ys))/2;  cz = (min(zs)+max(zs))/2

    # Offset: origin rispetto al centro geometrico
    ox = obj.location.x - cx
    oy = obj.location.y - cy
    oz = obj.location.z - cz

    if anchor == 'center':
        obj.location = (target_x + ox, target_y + oy, target_z + oz)
    elif anchor == 'bottom':
        bottom_from_center = cz - min(zs)
        obj.location = (target_x + ox, target_y + oy, target_z + oz + bottom_from_center)
    elif anchor == 'top':
        top_from_center = max(zs) - cz
        obj.location = (target_x + ox, target_y + oy, target_z + oz - top_from_center)

# Uso:
# apple = bpy.data.objects["Apple"]
# safe_place(apple, -0.08, 0.05, 0.05, anchor='bottom')
# → la BASE della mela è ora a z=0.05 nel mondo, indipendentemente dall'origin
```

### Normalizza una scena problematica

```python
# Per risolvere problemi di origin in blocco:
def normalize_origins(obj_names):
    """Sposta gli origins al centro di tutti gli oggetti in lista."""
    for name in obj_names:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            # Da questo punto: obj.location = centro mondo dell'oggetto ✓

# Chiama all'inizio di ogni script che modificherà le posizioni
normalize_origins(["Apple", "Pear", "Banana", "Pineapple"])
```

---

## NORMALI IN WORLD SPACE

Le normali **non** si trasformano con `matrix_world` — serve la **normal matrix** (transposta dell'inversa).

```python
from mathutils import Vector

# ── PERCHÉ NON matrix_world? ────────────────────────────────────
# Se l'oggetto ha scala non uniforme (es. scale=(2, 1, 1)),
# matrix_world distorce le normali. La normal matrix corregge.

def normal_matrix(obj):
    """Normal matrix = M^{-T} (inversa trasposta della parte 3x3)."""
    return obj.matrix_world.inverted().transposed().to_3x3()

# ── NORMALI DEI VERTICI IN WORLD SPACE ──────────────────────────
def vertex_normals_world(obj):
    """Restituisce lista di (world_pos, world_normal) per ogni vertice."""
    mw  = obj.matrix_world
    nm  = normal_matrix(obj)
    return [
        (mw @ v.co, (nm @ v.normal).normalized())
        for v in obj.data.vertices
    ]

# ── NORMALI DELLE FACCE IN WORLD SPACE ──────────────────────────
def face_normals_world(obj):
    """Restituisce lista di (world_center, world_normal) per ogni faccia."""
    mw  = obj.matrix_world
    nm  = normal_matrix(obj)
    return [
        (mw @ poly.center, (nm @ poly.normal).normalized())
        for poly in obj.data.polygons
    ]

# ── AGGIORNARE LE NORMALI DOPO MODIFICA ─────────────────────────
# Dopo aver spostato vertici programmaticamente, aggiorna:
obj.data.update()                           # ricalcola normali
# oppure in edit mode:
# bpy.ops.mesh.normals_make_consistent()

# ── DEBUG: visualizza normali come frecce ────────────────────────
# Utile per verificare orientamento prima di sculpting
"""
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.data.show_normal_vertex = True
        obj.data.show_normal_face = True
        obj.data.normal_length = 0.02
"""
```

---

## KDTREE — PROXIMITY QUERIES

Per trovare vertici vicini a un punto in **O(log n)** invece di O(n).

```python
from mathutils.kdtree import KDTree

# ── COSTRUZIONE ──────────────────────────────────────────────────
def build_kdtree(obj):
    """KDTree dai vertici dell'oggetto in world space."""
    mw          = obj.matrix_world
    verts_world = [mw @ v.co for v in obj.data.vertices]
    kd = KDTree(len(verts_world))
    for i, v in enumerate(verts_world):
        kd.insert(v, i)
    kd.balance()   # OBBLIGATORIO prima di usare find*
    return kd, verts_world

# ── QUERIES ──────────────────────────────────────────────────────
kd, verts_world = build_kdtree(obj)

# Il vertice più vicino a un punto
pos, idx, dist = kd.find((0.0, 0.0, 0.2))

# I 5 vertici più vicini
nearest_5 = kd.find_n((0.0, 0.0, 0.2), 5)
# → lista di (pos, index, dist)

# TUTTI i vertici entro raggio r (usato per brush sculpt)
in_range = kd.find_range((0.0, 0.0, 0.2), 0.05)
# → lista di (pos, index, dist)

# ── HELPER per brush ─────────────────────────────────────────────
def brush_vertices(obj, brush_center, brush_radius):
    """
    Indici e distanze dei vertici nel raggio del brush.
    Ritorna: [(vertex_index, distance), ...]
    """
    kd, _ = build_kdtree(obj)
    return [(idx, dist) for (pos, idx, dist) in kd.find_range(brush_center, brush_radius)]

# ── KDTree DA PIÙ OGGETTI (collision check) ───────────────────────
def build_scene_kdtree(objects):
    """KDTree globale da più oggetti. idx = (obj_idx, vert_idx)."""
    all_verts = []
    for oi, obj in enumerate(objects):
        mw = obj.matrix_world
        for vi, v in enumerate(obj.data.vertices):
            all_verts.append(((oi, vi), mw @ v.co))
    kd = KDTree(len(all_verts))
    for i, (key, pos) in enumerate(all_verts):
        kd.insert(pos, i)
    kd.balance()
    return kd, [item[0] for item in all_verts]
```

---

## FALLOFF — FUNZIONI DI INFLUENZA

Dato `dist` (distanza dal centro brush) e `radius`, restituisce un peso `∈ [0,1]`.
`weight=1` → vertice al centro, massima influenza. `weight=0` → oltre il bordo.

```python
import math

def falloff_smooth(dist, radius):
    """Smooth (Blender default) — curva a S, transizione naturale."""
    t = min(dist / radius, 1.0)
    return 1.0 - (3*t*t - 2*t*t*t)       # smoothstep

def falloff_sphere(dist, radius):
    """Sphere — decadimento sferico, classico per inflate/deflate."""
    t = min(dist / radius, 1.0)
    return math.sqrt(max(0.0, 1.0 - t*t))

def falloff_linear(dist, radius):
    """Linear — influenza proporzionale alla distanza."""
    return max(0.0, 1.0 - dist / radius)

def falloff_sharp(dist, radius):
    """Sharp — influenza concentrata vicino al centro."""
    t = min(dist / radius, 1.0)
    return (1.0 - t) ** 3

def falloff_gaussian(dist, radius, sigma=0.35):
    """Gaussian — bordo morbidissimo, ideale per blend sottili."""
    t = dist / radius
    return math.exp(-(t * t) / (2 * sigma * sigma))

def falloff_constant(dist, radius):
    """Constant (Blender 'flat') — tutti i vertici nel raggio = stesso peso."""
    return 1.0 if dist <= radius else 0.0

# ── TABELLA COMPARATIVA ──────────────────────────────────────────
# falloff_smooth   → bordo sfumato, forma a campana piatta  ████▄▄
# falloff_sphere   → cade più veloce verso il bordo        ████▃▁
# falloff_linear   → cade uniformemente                    ████▂▁
# falloff_sharp    → molto concentrato al centro           ██▂▁▁▁
# falloff_gaussian → bordo quasi impercettibile            █████▃
# falloff_constant → taglio netto al bordo                 █████▁

FALLOFFS = {
    'smooth':   falloff_smooth,
    'sphere':   falloff_sphere,
    'linear':   falloff_linear,
    'sharp':    falloff_sharp,
    'gaussian': falloff_gaussian,
    'constant': falloff_constant,
}
```

---

## SCULPT BRUSH PROCEDURALE

Combinazione di Normali + KDTree + Falloff = brush sculpt completo.

```python
def sculpt_brush(obj, brush_center, brush_radius, strength=0.01,
                 direction='normal', falloff='smooth'):
    """
    Sposta i vertici nel raggio del brush.

    brush_center : (x, y, z) in WORLD SPACE — centro del pennello
    brush_radius : float — raggio di influenza in world units
    strength     : float — intensità (positivo = gonfia/alza, negativo = sgonfia/abbassa)
    direction    : 'normal'  → lungo la normale del vertice (inflate)
                   'z'       → puro asse Z (flatten/raise)
                   (x, y, z) → direzione world personalizzata
    falloff      : 'smooth' | 'sphere' | 'linear' | 'sharp' | 'gaussian' | 'constant'
    """
    mw      = obj.matrix_world
    mw_inv  = mw.inverted()
    nm      = mw.inverted().transposed().to_3x3()   # normal matrix
    fn      = FALLOFFS.get(falloff, falloff_smooth)

    nearby = brush_vertices(obj, brush_center, brush_radius)
    if not nearby:
        return 0   # nessun vertice nel raggio

    for vi, dist in nearby:
        v      = obj.data.vertices[vi]
        weight = fn(dist, brush_radius)

        if direction == 'normal':
            disp_world = (nm @ v.normal).normalized() * strength * weight
        elif direction == 'z':
            disp_world = Vector((0, 0, strength * weight))
        else:
            disp_world = Vector(direction).normalized() * strength * weight

        # Spostamento in LOCAL space (dove vivono v.co)
        v.co += mw_inv.to_3x3() @ disp_world

    obj.data.update()   # ricalcola normali
    return len(nearby)

# ── ESEMPI D'USO ─────────────────────────────────────────────────

# 1. Gonfia una sfera in un punto (inflate)
# n = sculpt_brush(sphere, brush_center=(0, 0, 0.5), brush_radius=0.1, strength=0.02)

# 2. Abbassa la superficie (deflate)
# sculpt_brush(obj, center, 0.08, strength=-0.015, direction='normal')

# 3. Alza in puro Z (flatten raise)
# sculpt_brush(obj, center, 0.12, strength=0.01, direction='z', falloff='constant')

# 4. Graffio direzionale personalizzato
# sculpt_brush(obj, center, 0.05, strength=0.03, direction=(1, 0, 0.5))

# ── MULTI-PASS (simula pennellata continua) ───────────────────────
def paint_stroke(obj, points, radius, strength=0.01, **kwargs):
    """
    Applica il brush lungo una lista di punti (simulazione drag).
    points: lista di (x, y, z) world space
    """
    total = 0
    for pt in points:
        total += sculpt_brush(obj, pt, radius, strength, **kwargs)
    return total

# Stroke diagonale in 10 passi
# import numpy as np
# stroke = [(t*0.3, 0, 0.2) for t in np.linspace(0, 1, 10)]
# paint_stroke(sphere, stroke, radius=0.05, strength=0.015)
```

---

## CHEATSHEET — FORMULE RAPIDE

| Cosa vuoi sapere | Codice |
|------------------|--------|
| Posizione reale top oggetto | `max(v.z for v in [obj.matrix_world @ v.co for v in obj.data.vertices])` |
| Posizione reale base | `min(v.z for v in [obj.matrix_world @ v.co for v in obj.data.vertices])` |
| Altezza reale | `obj.dimensions.z` (world space se scale=1, altrimenti usa vertices) |
| Origin è al centro? | `abs(obj.location.z - world_center_z) < 0.001` |
| Distanza camera→punto | `(Vector(point) - cam.matrix_world.translation).length` |
| Ruota 45° intorno Z | `obj.rotation_euler.z += math.radians(45)` |
| Orienta verso punto | `obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()` |
| Applica scala | `bpy.ops.object.transform_apply(scale=True)` |
| Resetta tutto | `obj.location=(0,0,0); obj.rotation_euler=(0,0,0); obj.scale=(1,1,1)` |
| Normale vertice in world | `(obj.matrix_world.inverted().transposed().to_3x3() @ v.normal).normalized()` |
| Normale faccia in world | `(obj.matrix_world.inverted().transposed().to_3x3() @ poly.normal).normalized()` |
| Vertici entro raggio r | `KDTree(...).find_range(center, r)` → `[(pos, idx, dist)]` |
| Vertice più vicino | `KDTree(...).find(point)` → `(pos, idx, dist)` |
| Brush smooth weight | `1.0 - (3*t*t - 2*t*t*t)` dove `t = dist/radius` |
| Aggiorna mesh dopo edit | `obj.data.update()` |

---

## REGOLE D'ORO

1. **Misura prima di spostare** — usa `matrix_world @ v.co` per i bounds reali
2. **`obj.location` è l'origin, non il centro** — se fai bmesh manuale, l'origin è a (0,0,0)
3. **`origin_set(type='ORIGIN_GEOMETRY')` normalizza** — usala dopo la creazione
4. **`transform_apply` cambia i vertici** — dopo, location torna a (0,0,0) ma i vertici sono in world space
5. **`dimensions.z`** funziona solo se `scale=(1,1,1)`, altrimenti usa vertices
6. **Parent chain** — `matrix_world` include tutti i parent, `matrix_local` no
7. **Euler ha gimbal lock** — usa quaternion per rotazioni complesse (>90° multi-asse)
8. **Le normali NON si trasformano con `matrix_world`** — usa la normal matrix `M^{-T}` (inversa trasposta)
9. **KDTree per proximity** — brute force O(n) per ogni brush stroke è proibitivo; `build_kdtree()` una volta, poi `find_range()` O(log n)
10. **Sempre `obj.data.update()` dopo edit vertici** — senza, le normali restano vecchie e il rendering è sbagliato
