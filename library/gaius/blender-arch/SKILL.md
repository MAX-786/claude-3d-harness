---
description: >
  Skill avanzata per modellazione 3D in Blender — architettura, oggetti,
  prodotti, mobili, veicoli. Tecnica professionale: bevel, SubSurf, Boolean,
  bmesh, Array, Curve, Solidify, smooth shading. Visual loop con MCP connector
  (porta 9876, predefinito) o HTTP fallback (porta 7234): esegui → render → analizza → itera.
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - mcp__Blender__execute_blender_code
  - mcp__Blender__get_screenshot_of_window_as_image
  - mcp__Blender__get_screenshot_of_area_as_image
  - mcp__Blender__render_viewport_to_path
  - mcp__Blender__render_thumbnail_to_path
  - mcp__Blender__get_objects_summary
  - mcp__Blender__get_object_detail_summary
  - mcp__Blender__jump_to_view3d_object_by_name
---

# Skill: Blender 3D Modeling (Advanced)

Sei un esperto di modellazione 3D in Blender con Python (`bpy` + `bmesh`).
Ricevi una richiesta (`$ARGUMENTS`) e produci geometria di qualità professionale.

---

## Connessione — MCP (predefinito) + HTTP (fallback)

### ✅ Metodo 1 — MCP Tool (PREFERITO, porta 9876)
Usa direttamente il tool `mcp__Blender__execute_blender_code`:
```python
# Esegui codice in Blender — assegna sempre result={...} per ricevere dati
mcp__Blender__execute_blender_code(code="""
import bpy
# ... il tuo codice ...
result = {"ok": True, "verts": len(me.vertices)}
""")

# Screenshot viewport (senza render)
mcp__Blender__get_screenshot_of_window_as_image()

# Render su file e visualizza
mcp__Blender__render_viewport_to_path(output_path="C:/Users/josia/Downloads/out.png")

# Lista oggetti in scena
mcp__Blender__get_objects_summary()
```

**Avvio server MCP in Blender** (se non ancora attivo):
```python
# Da eseguire via HTTP una tantum all'inizio della sessione
import bpy
bpy.context.preferences.system.use_online_access = True
bpy.ops.blmcp.server_start()
# Dopo questo, usa i tool MCP direttamente senza HTTP
```

### ⚠️ Metodo 2 — HTTP Fallback (porta 7234, solo se MCP non disponibile)
```python
import urllib.request, json

BLENDER_URL = "http://localhost:7234"

def blender(code, timeout=60):
    data = json.dumps({"code": code, "timeout": timeout}).encode()
    req  = urllib.request.Request(f"{BLENDER_URL}/execute", data=data,
                                  headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout + 10).read())
    if "error" in r: raise RuntimeError(r["error"])
    return r.get("ok")
```

---

## Visual Loop — MCP (esegui → screenshot → analizza → itera)

```
FLUSSO PREFERITO con MCP:
1. mcp__Blender__execute_blender_code(code=build_code)
2. mcp__Blender__render_viewport_to_path(output_path="...preview.png")
   oppure mcp__Blender__get_screenshot_of_window_as_image()  ← più veloce, no render
3. Read("...preview.png")  → analisi visiva
4. mcp__Blender__execute_blender_code(code=fix_code)  → itera

RENDER COMPLETO (EEVEE) — da usare per risultato finale:
```
```python
# Via MCP — esegui questo codice poi leggi il file con Read
render_code = """
import bpy
sc = bpy.context.scene
try:    sc.render.engine = "BLENDER_EEVEE_NEXT"
except: sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.filepath = "C:/Users/josia/Downloads/render_final.png"
sc.render.use_compositing = False
sc.view_settings.view_transform = "Filmic"
sc.view_settings.look = "Medium High Contrast"
bpy.ops.render.render(write_still=True)
result = {"saved": sc.render.filepath}
"""
# mcp__Blender__execute_blender_code(code=render_code)
# poi: Read("C:/Users/josia/Downloads/render_final.png")
```

---

## Pulizia scena
```python
CLEAR_SCENE = '''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for m in bpy.data.meshes:    bpy.data.meshes.remove(m)
for m in bpy.data.materials: bpy.data.materials.remove(m)
for c in bpy.data.collections: bpy.data.collections.remove(c)
'''
```

---

## MODELLAZIONE — Funzioni Base

### Helper universali
```python
import bpy, math, bmesh
from mathutils import Vector, Matrix

def new_obj(name, mesh):
    """Crea e linka oggetto con mesh."""
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def box(name, x, y, z, sx, sy, sz, mat=None):
    """Box con transform apply. Dimensioni reali (non half)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    o = bpy.context.active_object
    o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if mat: assign_mat(o, mat)
    return o

def cyl(name, x, y, z, r, h, verts=32, cap_fill='NGON', mat=None):
    """Cilindro: r=raggio, h=altezza, centrato in z."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=h, vertices=verts,
        cap_fill_type=cap_fill, location=(x, y, z))
    o = bpy.context.active_object; o.name = name
    if mat: assign_mat(o, mat)
    return o

def sphere(name, x, y, z, r, subdiv=3, mat=None):
    """Icosfera: più uniforme della UV sphere."""
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=subdiv,
                                           location=(x, y, z))
    o = bpy.context.active_object; o.name = name
    smooth_shade(o)
    if mat: assign_mat(o, mat)
    return o

def plane(name, x, y, z, sx, sy, mat=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y, z))
    o = bpy.context.active_object; o.name = name
    o.scale = (sx, sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    if mat: assign_mat(o, mat)
    return o

def assign_mat(obj, mat):
    if obj.data.materials: obj.data.materials[0] = mat
    else: obj.data.materials.append(mat)
```

---

## MODELLAZIONE — Tecniche Avanzate

### Smooth shading + Auto Smooth

> ⚠️ **BUG CRITICO — `bpy.ops.object.shade_smooth()` NON funziona su mesh bmesh**
>
> L'operatore `bpy.ops.object.shade_smooth()` **non rimuove l'attributo `sharp_face`**
> su mesh create con bmesh. Risultato: tutte le facce rimangono piatte (`normals_domain=FACE`)
> e si vedono striature verticali pronunciate su cilindri, coni e oggetti lathe.
>
> **Diagnosi:**
> ```python
> ob.data.normals_domain  # → 'FACE' (sbagliato), deve essere 'POINT'
> 'sharp_face' in ob.data.attributes  # → True dopo ops.shade_smooth() → piatto!
> ```
>
> **Fix: usa il metodo diretto sul mesh, non l'operatore:**
> ```python
> # SBAGLIATO (non funziona su bmesh):
> bpy.ops.object.shade_smooth()   # → sharp_face rimane True, striature!
>
> # CORRETTO — metodo diretto sul mesh (Blender 4.x+):
> ob.data.shade_smooth()          # → rimuove sharp_face, normals_domain='POINT' ✓
>
> # CORRETTO con soglia angolo (marca edge acuti come sharp):
> ob.data.shade_smooth()                          # prima: abilita smooth su tutto
> ob.data.set_sharp_from_angle(angle=math.radians(30))  # poi: marca edge > 30° come sharp
> ```

```python
def smooth_shade(obj, angle_deg=30):
    """
    Smooth shading con soglia angolo. ESSENZIALE per oggetti organici e curvi.
    Senza questo: facce piatte visibili su cilindri e sfere.

    NOTA: usa ob.data.shade_smooth() (metodo mesh), NON bpy.ops.object.shade_smooth()
    che non funziona correttamente su mesh create con bmesh.
    """
    # CORRETTO: metodo diretto sul mesh data-block
    obj.data.shade_smooth()
    # Marca edge acuti come sharp (angolo > soglia)
    try:
        obj.data.set_sharp_from_angle(angle=math.radians(angle_deg))
    except AttributeError:
        # Blender < 4.1: fallback via modifier
        try:
            mod = obj.modifiers.new("SmoothAngle", "SMOOTH_BY_ANGLE")
            mod.angle = math.radians(angle_deg)
        except:
            pass
    obj.data.update()
```

### Bevel modifier — spigoli realistici
```python
def add_bevel(obj, amount=0.02, segments=2, limit='ANGLE', angle_deg=30):
    """
    REGOLA D'ORO: ogni oggetto reale ha spigoli smussati.
    amount  = 0.005–0.02  per oggetti piccoli (telefono, sedia)
    amount  = 0.05–0.15   per architettura (davanzali, cornici)
    segments = 2  → smussatura morbida con riflessi netti (product design)
    segments = 3+ → ultra morbido (auto, gadget)
    """
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width        = amount
    mod.segments     = segments
    mod.limit_method = limit
    if limit == 'ANGLE':
        mod.angle_limit = math.radians(angle_deg)
    mod.profile = 0.5   # profilo circolare
    return mod

# Esempio uso: tavolo con spigoli realistici
# t = box("Table", 0, 0, 0.75, 1.6, 0.8, 0.05)
# add_bevel(t, amount=0.008, segments=2)
# smooth_shade(t, 60)
```

### Subdivision Surface — forme organiche
```python
def add_subsurf(obj, levels=2, render_levels=3, simple=False):
    """
    Leviga la mesh per forme organiche.
    levels=1: leggera levigatura (mobili morbidi)
    levels=2: media (cuscini, corpi)
    levels=3: alta (personaggi, auto)
    ATTENZIONE: applicare DOPO il bevel. Mai su mesh con N-gon complessi.
    """
    mod = obj.modifiers.new("Subdivision", "SUBSURF")
    mod.levels          = levels
    mod.render_levels   = render_levels
    mod.subdivision_type = 'SIMPLE' if simple else 'CATMULL_CLARK'
    smooth_shade(obj)
    return mod
```

### Solidify — spessore a superfici piatte
```python
def add_solidify(obj, thickness=0.05, offset=-1.0):
    """
    Aggiunge spessore a mesh piatte: vetrate, pareti sottili, pannelli.
    offset=-1.0 → spessore verso l'interno
    offset= 0.0 → simmetrico
    offset=+1.0 → verso l'esterno
    """
    mod = obj.modifiers.new("Solidify", "SOLIDIFY")
    mod.thickness         = thickness
    mod.offset            = offset
    mod.use_even_offset   = True
    return mod
```

### Array modifier — elementi ripetuti
```python
def add_array(obj, count=5, offset_x=0, offset_y=0, offset_z=0,
              relative=True):
    """
    Moltiplica oggetto lungo un asse.
    relative=True: offset come multiplo della dimensione oggetto
    relative=False: offset assoluto in metri

    Usi tipici:
    - Ringhiera: count=20, offset_x=1.0 (relativo)
    - Finestre ripetute: count=5, offset_x=3.0 (assoluto)
    - Listelli solaio: count=15, offset_y=1.0 (relativo)
    """
    mod = obj.modifiers.new("Array", "ARRAY")
    mod.count = count
    if relative:
        mod.use_relative_offset = True
        mod.relative_offset_displace = (offset_x, offset_y, offset_z)
    else:
        mod.use_relative_offset  = False
        mod.use_constant_offset  = True
        mod.constant_offset_displace = (offset_x, offset_y, offset_z)
    return mod

# Esempio: ringhiera balcone
# palo = cyl("Palo", 0, 0, 0.5, 0.02, 1.0, verts=8)
# add_array(palo, count=20, offset_x=1.0)   # 20 pali spaziati di 1 dim
# barra = box("Barra", 0, 0, 1.0, 0.02, 0.04, 0.04)
# add_array(barra, count=1, relative=False, offset_x=19*spazio)
```

### Mirror modifier
```python
def add_mirror(obj, axis_x=True, axis_y=False, axis_z=False,
               merge=True, threshold=0.001):
    """Specchia oggetto. Modella solo metà → risparmio tempo."""
    mod = obj.modifiers.new("Mirror", "MIRROR")
    mod.use_axis         = (axis_x, axis_y, axis_z)
    mod.use_merge_center = merge
    mod.merge_threshold  = threshold
    return mod
```

### Boolean — tagli e unioni
```python
def boolean_cut(target, cutter, apply=True):
    """
    Taglia target con forma del cutter (finestre in muri, buchi, nicchie).
    IMPORTANTE: entrambi devono avere manifold mesh (no fori, no face invertite).
    """
    mod = target.modifiers.new("Boolean", "BOOLEAN")
    mod.operation = 'DIFFERENCE'
    mod.object    = cutter
    mod.solver    = 'FAST'   # EXACT più preciso ma più lento
    if apply:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier="Boolean")
        bpy.data.objects.remove(cutter, do_unlink=True)
    return mod

# Esempio: finestra nel muro
# muro  = box("Muro", 0, 0, 1.5, 6, 0.3, 3.0)
# taglio = box("Cut_Finestra", 1.0, 0, 1.5, 1.4, 1.0, 1.2)
# boolean_cut(muro, taglio)
# vetro = box("Vetro", 1.0, 0.02, 1.5, 1.4, 0.04, 1.2, mat_glass)
```

### bmesh — geometria personalizzata
```python
def make_mesh_from_data(name, verts, faces, edges=[], smooth=False, mat=None):
    """
    Crea mesh da liste verts/faces. Massimo controllo sulla topologia.
    verts: [(x,y,z), ...]
    faces: [(i,j,k,...), ...] — CCW per normali verso l'esterno
    """
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    if smooth: smooth_shade(obj)
    if mat: assign_mat(obj, mat)
    # Normalizza normali
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj

def bmesh_extrude(name, profile_verts_2d, depth, axis='Y', mat=None):
    """
    Estrude un profilo 2D lungo un asse.
    Utile per: cornici, modanature, profili architettonici.
    profile_verts_2d: [(x, z), ...] nel piano XZ
    """
    bm = bmesh.new()
    v0_list = [bm.verts.new((x, 0, z)) for x, z in profile_verts_2d]
    v1_list = [bm.verts.new((x, depth, z)) for x, z in profile_verts_2d]
    bm.verts.ensure_lookup_table()
    n = len(profile_verts_2d)
    # Facce laterali
    for i in range(n - 1):
        bm.faces.new([v0_list[i], v0_list[i+1], v1_list[i+1], v1_list[i]])
    # Cap start e end
    bm.faces.new(list(reversed(v0_list)))
    bm.faces.new(v1_list)
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat: assign_mat(obj, mat)
    return obj
```

### Curve — tubi, cavi, ringhiere su percorso
```python
def pipe_along_points(name, points, radius=0.02, resolution=12, mat=None):
    """
    Crea un tubo/cavo che segue una serie di punti 3D.
    Utile per: tubature, cavi elettrici, ringhiere curve, scale.
    points: [(x,y,z), ...]
    """
    curve_data = bpy.data.curves.new(name + "_curve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode  = 'FULL'
    curve_data.bevel_depth    = radius
    curve_data.bevel_resolution = resolution
    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(points) - 1)
    for i, (x, y, z) in enumerate(points):
        spline.points[i].co = (x, y, z, 1)
    spline.use_endpoint_u = True
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    if mat: assign_mat(obj, mat)
    return obj
```

---

## POSIZIONAMENTO PRECISO — Attach Point System

> **Teoria:** ogni oggetto Blender ha una **base ortonormale** propria incorporata nella
> `matrix_world` (4×4). Per far toccare due oggetti con precisione si calcolano i punti
> di contatto nel frame locale di ciascun oggetto e si trasformano nel frame world comune.
>
> ```
> p_world = obj.matrix_world @ p_local        # locale → world
> p_local = obj.matrix_world.inverted() @ p_world  # world → locale
> ```
> Precisione verificata: errore residuo < 0.15 μm anche con oggetti ruotati.

```python
from mathutils import Vector
import bpy

# ── Conversioni frame ─────────────────────────────────────────────────

def local_to_world(obj, p_local):
    """Trasforma un punto dal frame locale dell'oggetto al world frame."""
    bpy.context.view_layer.update()
    return obj.matrix_world @ Vector(p_local)

def world_to_local(obj, p_world):
    """Trasforma un punto dal world frame al frame locale dell'oggetto."""
    bpy.context.view_layer.update()
    return obj.matrix_world.inverted() @ Vector(p_world)

def world_bounds(obj):
    """
    Restituisce il bounding box world-space dell'oggetto.
    Returns: dict con 'min', 'max', 'center', 'size' (tutti Vector)
    """
    bpy.context.view_layer.update()
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    mn = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    mx = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    return {'min': mn, 'max': mx, 'center': (mn + mx) / 2, 'size': mx - mn}

# ── Attach point — posizionamento preciso ─────────────────────────────

def attach_to(obj_b, pt_b_local, obj_a, pt_a_local,
              align=False, gap=0.0, gap_axis=None):
    """
    Posiziona obj_b in modo che il suo punto locale `pt_b_local`
    coincida esattamente con il punto locale `pt_a_local` di obj_a.

    Args:
        obj_b      : oggetto da spostare
        pt_b_local : punto di attacco su obj_b in coordinate LOCALI  (tuple o Vector)
        obj_a      : oggetto di riferimento (fisso)
        pt_a_local : punto di attacco su obj_a in coordinate LOCALI  (tuple o Vector)
        align      : se True, copia anche la rotazione di obj_a su obj_b
        gap        : offset aggiuntivo dopo il contatto (in metri)
        gap_axis   : direzione world del gap (Vector); se None usa la direzione delta

    Returns:
        float: distanza residua tra i punti di attacco (< 1e-7 m = precisione macchina)

    Esempi:
        # Piattino: il suo top (z_local = saucer_h) tocca il bottom della tazza (z_local = 0)
        attach_to(saucer, (0, 0, 0.016), cup, (0, 0, 0))

        # Manico: il suo start (z_local = ATZ_TOP) tocca la parete destra della tazza
        attach_to(handle, (0.031, 0, 0.048), cup, (0.031, 0, 0.048))

        # Coperchio 2mm sopra il bordo
        attach_to(lid, (0, 0, -0.01), mug, (0, 0, 0.09), gap=0.002, gap_axis=(0,0,1))
    """
    bpy.context.view_layer.update()

    # 1. Punto target nel world frame
    p_target = obj_a.matrix_world @ Vector(pt_a_local)

    # 2. (Opzionale) allinea rotazione di B a quella di A
    if align:
        obj_b.rotation_mode = 'QUATERNION'
        obj_b.rotation_quaternion = obj_a.matrix_world.to_quaternion()
        bpy.context.view_layer.update()

    # 3. Posizione attuale del punto di attacco di B nel world
    p_now = obj_b.matrix_world @ Vector(pt_b_local)

    # 4. Delta world-space da applicare
    delta_world = p_target - p_now

    # 5. Applica gap
    if gap != 0.0:
        if gap_axis is not None:
            delta_world += Vector(gap_axis).normalized() * gap
        elif delta_world.length > 1e-10:
            delta_world += delta_world.normalized() * gap

    # 6. Converti in parent space se necessario, poi aggiorna location
    if obj_b.parent:
        delta = obj_b.parent.matrix_world.inverted().to_3x3() @ delta_world
    else:
        delta = delta_world
    obj_b.location = obj_b.location + delta
    bpy.context.view_layer.update()

    # 7. Calcola residuo
    p_a_f = obj_a.matrix_world @ Vector(pt_a_local)
    p_b_f = obj_b.matrix_world @ Vector(pt_b_local)
    return (p_b_f - p_a_f).length


def attach_bounds(obj_b, face_b, obj_a, face_a, gap=0.0):
    """
    Posiziona obj_b in modo che la faccia `face_b` del suo bounding box
    tocchi la faccia `face_a` del bounding box di obj_a nel world space.

    face: 'top' | 'bottom' | 'front' | 'back' | 'right' | 'left'

    Esempi:
        attach_bounds(saucer, 'top', cup, 'bottom')
        # → top del piattino tocca il bottom della tazza

        attach_bounds(lid, 'bottom', mug, 'top', gap=0.002)
        # → coperchio 2mm sopra il bordo
    """
    AXIS   = {'top': 2, 'bottom': 2, 'front': 1, 'back': 1, 'right': 0, 'left': 0}
    IS_MAX = {'top': True, 'right': True, 'back': True,
              'bottom': False, 'left': False, 'front': False}
    bpy.context.view_layer.update()

    ax    = AXIS[face_a]
    va    = [obj_a.matrix_world @ v.co for v in obj_a.data.vertices]
    vb    = [obj_b.matrix_world @ v.co for v in obj_b.data.vertices]
    ext_a = max(v[ax] for v in va) if IS_MAX[face_a] else min(v[ax] for v in va)
    ext_b = max(v[ax] for v in vb) if IS_MAX[face_b] else min(v[ax] for v in vb)
    delta_ax = ext_a - ext_b + gap * (1 if IS_MAX[face_a] else -1)

    if obj_b.parent:
        world_d = [0, 0, 0]; world_d[ax] = delta_ax
        obj_b.location += obj_b.parent.matrix_world.inverted().to_3x3() @ Vector(world_d)
    else:
        obj_b.location[ax] += delta_ax

    bpy.context.view_layer.update()
    vb2   = [obj_b.matrix_world @ v.co for v in obj_b.data.vertices]
    ext_b2 = max(v[ax] for v in vb2) if IS_MAX[face_b] else min(v[ax] for v in vb2)
    return abs(ext_b2 - ext_a)   # residuo (< 1e-7 = ok)
```

### Pattern tipici di attacco

```python
# ── Stack: B sopra A (via bounds) ─────────────────────────────
attach_bounds(obj_b, 'bottom', obj_a, 'top')

# ── Stack con gap ─────────────────────────────────────────────
attach_bounds(lid, 'bottom', mug, 'top', gap=0.002)

# ── Punto preciso (local frame): piattino sotto tazza ─────────
# Il top del piattino (z_local=saucer_height) tocca il bottom della tazza (z_local=0)
attach_to(saucer, (0, 0, 0.016), cup, (0, 0, 0.0))

# ── Verifica dopo posizionamento ──────────────────────────────
b = world_bounds(obj)
print(f"bottom z = {b['min'].z:.6f}")
print(f"top    z = {b['max'].z:.6f}")
print(f"center   = {b['center']}")

# ── Trasformazioni frame ──────────────────────────────────────
# "Dove si trova il bordo del rim della tazza nel world space?"
rim_world = local_to_world(cup, (0.031, 0, 0.058))

# "Dato un punto world, dove è nelle coordinate locali del piattino?"
p_local = world_to_local(saucer, rim_world)
```

---

## PARADIGMA PANNELLI / CUCITURE — `assembly_kernel`

> **Quando (GATE):** oggetto manifatturiero **costruito da pannelli
> piatti/curvi uniti da cuciture** — calzature, borse, imbottiti, scocche,
> guanti. **Quando NON:** forma organica a superficie unica (→ sculpt /
> procedural), primitiva con modificatori (→ sezioni sopra), tubo/spine
> (→ procedural). Se il gate è soddisfatto, **NON modellare l'oggetto come
> un loft o boolean singolo "tutto in uno"**: è la causa-radice del
> fallimento "calzino" (superficie a calzino senza struttura, cuciture
> disallineate, sorgenti non sincronizzate). Si usa il kernel.

**Principio (3 livelli ORTOGONALI, validati con metriche):**
1. **Placement** = 1 matrice **rigida** SE(3) (`Frame`); la *dimensione* sta
   nel locale, MAI scala non uniforme nella matrice.
2. **Cuciture** = entità **condivise** possedute dall'assieme:
   `SeamCurve` (1-D) e `JunctionPoint` (0-D, dove ≥2 seam convergono).
   Ogni pannello adiacente **rigenera il bordo SU** il connettore condiviso
   — non lo autora per conto suo (questo elimina i gap per costruzione).
3. **Forma interna / curvatura** = un **campo di frame** anti-drift
   (`parallel_transport`) lungo una spine locale. Curvatura forte ⇒
   obbligatorio il frame-field; un frame singolo regge solo il ~piatto.
   Una forma complessa **emerge** dalla composizione di pochi pezzi curvi
   semplici, NON da un colpo solo.

**Modulo:** `D:\blender-claude\kernel\assembly_kernel.py` (Blender 5.x).
```python
import sys; sys.path.insert(0, r"D:\blender-claude\kernel")
import assembly_kernel as ak
import importlib; importlib.reload(ak)

A = ak.Assembly("Stivale")              # nome → prefisso "Asm_" (bbox-frame)
# 1) base globale = un "last" (forma del piede) come master surface
#    last(t,a) -> Vector globale  (t lungo, a sezione)
# 2) cuciture REALI del bootmaking come connettori CONDIVISI:
seam_vq = A.seam("vamp_quarter", [last(0.42, a) for a in angoli])
jp_thr  = A.junction("throat", last(0.50, 0.0))
# 3) pannelli: bordi/angoli VINCOLATI ai connettori condivisi
A.panel_on_master(master_vamp, NR, NT, edge_t0=seam_vq, corner=jp_thr,
                  material=(0.05,0.03,0.02))           # mosaico per-pezzo
A.swept_piece(frame, spine_locale, half_w, NA,
              start_seam=seam_vq, material=(...))       # pezzo curvo
A.finalize(weld=True)                                   # 1 mesh, salda condivisi
m = A.validate()                                        # GATE oggettivo
assert m["components"] == 1 and m["nonmanifold"] == 0
ak.studio_setup()                                       # preset render leggibile
```

**Disciplina imposta dall'API:** i builder accettano *solo* `SeamCurve`/
`JunctionPoint` per i bordi/angoli vincolati. Se ti accorgi di calcolare un
bordo di cucitura "a mano" o di unire pezzi con boolean → stai sbagliando
paradigma: definisci una `SeamCurve` condivisa e lega entrambi i pannelli.

**Gate di consegna:** un assieme non è "fatto" finché `validate()` non dà
`components == 1`, `nonmanifold == 0` e i `boundary_edges` attesi (solo i
bordi realmente aperti). Renderizza sempre con `ak.studio_setup()` +
bbox-framing sugli oggetti `Asm_*` (preset leggibile fissato).

Fondamenti e prove: vedi memoria di progetto `assembly_kernel.md` /
`stitch_paradigm.md`. Mappa bootmaking → connettori: vamp|quarter, toe-cap,
throat (JunctionPoint), feather/linea di montaggio, topline, backstay.

---

## OGGETTI GENERICI — Pattern Riutilizzabili

### Sedia moderna
```python
def make_chair(name, x, y, z, mat_seat=None, mat_legs=None):
    """Sedia scandinava con 4 gambe, schienale, seduta."""
    parts = []

    # Seduta
    seat = box(f"{name}_Seat", x, y, z+0.45, 0.50, 0.50, 0.04, mat_seat)
    add_bevel(seat, 0.005, 2); parts.append(seat)

    # Schienale
    back = box(f"{name}_Back", x, y+0.23, z+0.72, 0.46, 0.04, 0.55, mat_seat)
    add_bevel(back, 0.005, 2); parts.append(back)

    # 4 gambe
    for lx, ly in [(-0.20,-0.20), (0.20,-0.20), (-0.20,0.20), (0.20,0.20)]:
        leg = cyl(f"{name}_Leg_{lx}{ly}", x+lx, y+ly, z+0.225, 0.018, 0.45, verts=8, mat=mat_legs)
        smooth_shade(leg); parts.append(leg)

    return parts

# sedia_mat = mat_wood("Legno_Chiaro", (0.65, 0.42, 0.20))
# make_chair("Sedia1", 0, 0, 0, sedia_mat, sedia_mat)
```

### Tavolo
```python
def make_table(name, x, y, z, w=1.6, d=0.85, h=0.74,
               mat_top=None, mat_legs=None):
    """Tavolo rettangolare con 4 gambe."""
    top = box(f"{name}_Top", x, y, z+h, w, d, 0.04, mat_top)
    add_bevel(top, 0.006, 2)
    for lx, ly in [(-w/2+0.06, -d/2+0.06), (w/2-0.06, -d/2+0.06),
                   (-w/2+0.06,  d/2-0.06), (w/2-0.06,  d/2-0.06)]:
        leg = box(f"{name}_Leg_{lx:.2f}", x+lx, y+ly, z+h/2-0.02, 0.06, 0.06, h-0.04, mat_legs)
        add_bevel(leg, 0.004, 2)
```

### Lampada da pavimento
```python
def make_floor_lamp(name, x, y, z=0, mat_pole=None, mat_shade=None):
    """Lampada da pavimento: base, asta, paralume conico."""
    # Base
    base = cyl(f"{name}_Base", x, y, z+0.04, 0.15, 0.08, verts=24, mat=mat_pole)
    smooth_shade(base); add_bevel(base, 0.01, 2)
    # Asta
    pole = cyl(f"{name}_Pole", x, y, z+0.8, 0.015, 1.5, verts=16, mat=mat_pole)
    smooth_shade(pole)
    # Paralume (cono)
    bpy.ops.mesh.primitive_cone_add(radius1=0.25, radius2=0.08, depth=0.3,
                                    location=(x, y, z+1.65))
    shade = bpy.context.active_object; shade.name = f"{name}_Shade"
    smooth_shade(shade)
    if mat_shade: assign_mat(shade, mat_shade)
    # Luce interna
    bpy.ops.object.light_add(type='POINT', location=(x, y, z+1.58))
    bulb = bpy.context.active_object; bulb.name = f"{name}_Light"
    bulb.data.energy = 150; bulb.data.color = (1.0, 0.92, 0.75)
    bulb.data.shadow_soft_size = 0.05
```

### Oggetto cilindrico (bottiglia, vaso, tazza)
```python
def make_lathe_object(name, x, y, z, profile_rz, mat=None, smooth=True):
    """
    Crea oggetto di rivoluzione da profilo [(r, z), ...].
    Usa bmesh per massima precisione.
    profile_rz: lista di (raggio, altezza_z) dal basso verso l'alto.

    Esempio tazza:
    profile = [(0,0),(0.04,0),(0.045,0.02),(0.045,0.08),
               (0.04,0.09),(0.035,0.1),(0.035,0.09),(0,0.09)]
    make_lathe_object("Tazza", 0,0,0, profile, mat_ceramic)
    """
    segments = 32
    bm = bmesh.new()
    verts_rings = []
    for r, zz in profile_rz:
        ring = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            vx = r * math.cos(angle)
            vy = r * math.sin(angle)
            ring.append(bm.verts.new((x + vx, y + vy, z + zz)))
        verts_rings.append(ring)
    bm.verts.ensure_lookup_table()
    for ri in range(len(verts_rings) - 1):
        r0, r1 = verts_rings[ri], verts_rings[ri + 1]
        for j in range(segments):
            nj = (j + 1) % segments
            bm.faces.new([r0[j], r0[nj], r1[nj], r1[j]])
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if smooth: smooth_shade(obj)
    if mat: assign_mat(obj, mat)
    return obj
```

---

## ARCHITETTURA — Pattern Aggiornati

### Muro con apertura (Boolean corretto)
```python
def wall_with_openings(name, x, y, z_base, width, thickness, height,
                       openings, mat_wall=None):
    """
    Muro con finestre/porte ricavate per Boolean.
    openings: [{'x': offset, 'z': bottom, 'w': width, 'h': height}, ...]

    Più realistico dei box separati perché il muro è un solido continuo.
    """
    wall = box(name, x, y, z_base + height/2, width, thickness, height, mat_wall)

    for i, op in enumerate(openings):
        cut = box(f"{name}_Cut_{i}",
                  x + op['x'] - width/2, y,
                  z_base + op['z'] + op['h']/2,
                  op['w'], thickness * 2, op['h'])
        bpy.context.view_layer.objects.active = wall
        mod = wall.modifiers.new(f"Cut_{i}", "BOOLEAN")
        mod.operation = 'DIFFERENCE'
        mod.object    = cut
        mod.solver    = 'FAST'
        bpy.ops.object.modifier_apply(modifier=f"Cut_{i}")
        bpy.data.objects.remove(cut, do_unlink=True)
    return wall

# Esempio:
# wall_with_openings("Facciata", 0, -4, 0, 10, 0.3, 3.0, [
#     {'x': 2.0, 'z': 0.8, 'w': 1.4, 'h': 1.2},   # finestra sinistra
#     {'x': 5.0, 'z': 0.8, 'w': 1.4, 'h': 1.2},   # finestra destra
#     {'x': 0.5, 'z': 0.0, 'w': 1.0, 'h': 2.1},   # porta
# ], mat_concrete)
```

### Cornice finestra
```python
def window_frame(name, x, y, z, w, h, depth=0.15,
                 frame_w=0.06, mat_frame=None, mat_glass=None):
    """
    Finestra completa: telaio (4 profili) + vetro.
    frame_w: larghezza profilo del telaio
    """
    # Montanti verticali
    for side, ox in [("L", -(w/2 - frame_w/2)), ("R", w/2 - frame_w/2)]:
        b = box(f"{name}_Frame_{side}", x+ox, y, z, frame_w, depth, h, mat_frame)
        add_bevel(b, 0.004, 2)
    # Traversi orizzontali
    inner_w = w - 2 * frame_w
    for side, oz in [("B", -(h/2 - frame_w/2)), ("T", h/2 - frame_w/2)]:
        b = box(f"{name}_Frame_{side}", x, y, z+oz, inner_w, depth, frame_w, mat_frame)
        add_bevel(b, 0.004, 2)
    # Vetro
    glass = box(f"{name}_Glass", x, y, z, inner_w, depth*0.1, h - 2*frame_w, mat_glass)
    add_solidify(glass, 0.006)
    return glass
```

### Ringhiera parametrica
```python
def railing(name, x_start, x_end, y, z_base, height=1.0,
            post_spacing=1.0, post_r=0.025, bar_r=0.015, mat=None):
    """
    Ringhiera con pali e barra orizzontale.
    Usa Array modifier per i pali → efficiente e modificabile.
    """
    length = x_end - x_start
    n_posts = max(2, int(length / post_spacing) + 1)
    spacing = length / (n_posts - 1)

    # Palo singolo + array
    post = cyl(f"{name}_Post", x_start, y, z_base + height/2,
               post_r, height, verts=8, mat=mat)
    smooth_shade(post)
    if n_posts > 1:
        add_array(post, count=n_posts, relative=False,
                  offset_x=spacing, offset_y=0, offset_z=0)

    # Barra orizzontale
    bar = pipe_along_points(f"{name}_Bar",
        [(x_start, y, z_base + height),
         (x_end,   y, z_base + height)],
        radius=bar_r, mat=mat)

    # Barra inferiore
    bar_low = pipe_along_points(f"{name}_Bar_Low",
        [(x_start, y, z_base + 0.08),
         (x_end,   y, z_base + 0.08)],
        radius=bar_r, mat=mat)
    return post, bar, bar_low
```

### Scala a rampa
```python
def staircase(name, x, y, z_bottom, z_top, width, depth_total,
              mat_step=None, mat_riser=None):
    """
    Scala lineare con pedate e alzate.
    Scende da z_top a z_bottom su profondità depth_total.
    """
    n_steps = max(3, round((z_top - z_bottom) / 0.175))
    step_h  = (z_top - z_bottom) / n_steps
    step_d  = depth_total / n_steps
    parts   = []
    for i in range(n_steps):
        # Pedata
        pz = z_bottom + (i + 1) * step_h
        py = y + depth_total - (i + 0.5) * step_d
        tread = box(f"{name}_Tread_{i}", x, py, pz - step_h/2 + 0.02,
                    width, step_d, 0.04, mat_step)
        add_bevel(tread, 0.005, 2); parts.append(tread)
        # Alzata (opzionale, per scale chiuse)
        if mat_riser:
            riser = box(f"{name}_Riser_{i}", x, py + step_d/2 - 0.02,
                        pz - step_h/2, width, 0.04, step_h, mat_riser)
            parts.append(riser)
    return parts
```

### Tetto a padiglione (hip roof)
```python
def hip_roof(name, cx, cy, z_eave, W, D, rise, overhang=0.5, mat=None):
    hw = W/2 + overhang;  hd = D/2 + overhang
    rl = max((W - D)/2, 0.8);  zr = z_eave + rise
    v = [(cx-hw,cy-hd,z_eave),(cx+hw,cy-hd,z_eave),
         (cx+hw,cy+hd,z_eave),(cx-hw,cy+hd,z_eave),
         (cx-rl,cy,zr),(cx+rl,cy,zr)]
    f = [(0,1,5,4),(2,3,4,5),(4,3,0),(1,2,5)]
    obj = make_mesh_from_data(name, v, f)
    if mat: assign_mat(obj, mat)
    return obj
```

### Barra diagonale XZ (X-frame, croce di Sant'Andrea)
```python
def diag_bar_xz(name, x1, z1, x2, z2, y_wall,
                thickness=0.048, depth=0.07, mat=None):
    """
    Barra diagonale piatta su parete frontale (piano XZ).
    NON usare box ruotati — proiettano la lunghezza in Y.
    """
    dx=x2-x1; dz=z2-z1; ln=math.sqrt(dx*dx+dz*dz)
    if ln < 1e-6: return None
    dx/=ln; dz/=ln; px=-dz; pz=dx
    mx=(x1+x2)/2; mz=(z1+z2)/2
    hl=ln/2; ht=thickness/2; hd=depth/2
    verts = []
    for sl in (-hl, hl):
        for st in (-ht, ht):
            for sd in (-hd, hd):
                verts.append((mx+sl*dx+st*px, y_wall+sd, mz+sl*dz+st*pz))
    faces = [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    obj = make_mesh_from_data(name, verts, faces)
    if mat: assign_mat(obj, mat)
    return obj
```

---

## MATERIALI

> **Blender 5.x API notes:**
> - `blend_method` è **DEPRECATO** → usa `surface_render_method = "BLENDED"` (trasparenza colorata) o `"DITHERED"` (compatibile con passes)
> - `use_nodes` setter è deprecated (5.0+), ma la proprietà esiste ancora
> - Principled BSDF ora usa modello **OpenPBR**: ha layer Coat (clearcoat), Sheen, Subsurface migliorato
> - Input sicuro: controlla `if 'Nome' in [i.name for i in bsdf.inputs]` per versione-safety
> - **`ShaderNodeMixRGB` è DEPRECATO** in Blender 5.x → usa `ShaderNodeMix` con `node.data_type = 'RGBA'`. Gli input cambiano: `inputs[0]` = Factor, `inputs[6]` = Color A, `inputs[7]` = Color B, `outputs[2]` = Color. Con MixRGB il nodo esiste ma restituisce valori di default (giallo) invece del mix corretto — bug silenzioso!
>
> ```python
> # SBAGLIATO (Blender 5.x):
> mix = nt.nodes.new('ShaderNodeMixRGB')
> mix.inputs[1].default_value = (1,0,0,1)  # → restituisce giallo default
>
> # CORRETTO (Blender 4.x+):
> mix = nt.nodes.new('ShaderNodeMix')
> mix.data_type = 'RGBA'
> mix.blend_type = 'MIX'
> mix.inputs[6].default_value = (1,0,0,1)   # Color A
> mix.inputs[7].default_value = (0,1,0,1)   # Color B
> nt.links.new(factor_socket, mix.inputs[0])
> nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
> ```

### Helper: accesso input sicuro
```python
def bsdf_set(bsdf, input_name, value):
    """Setta input BSDF solo se esiste (version-safe)."""
    input_names = [i.name for i in bsdf.inputs]
    if input_name in input_names:
        bsdf.inputs[input_name].default_value = value
```

### PBR base
```python
def mat_pbr(name, color, roughness=0.5, metallic=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; m.node_tree.nodes.clear()
    bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out  = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value  = roughness
    bsdf.inputs['Metallic'].default_value   = metallic
    if alpha < 1.0:
        # Blender 5.x: surface_render_method sostituisce blend_method
        try: m.surface_render_method = "BLENDED"
        except: m.blend_method = 'BLEND'   # fallback < 4.x
        bsdf.inputs['Alpha'].default_value = alpha
    return m
```

### Noise procedurale (calcestruzzo, marmo, roccia)
```python
def mat_noise(name, c1, c2, roughness=0.85, scale=8, distortion=0.1,
              noise_type='MULTIFRACTAL'):
    """
    Materiale con variazione procedurale.
    c1/c2: colori min/max della variazione.
    scale: densità rumore (6=grosso, 15=fine come marmo)

    noise_type (Blender 5.x ShaderNodeTexNoise):
      'MULTIFRACTAL'       → default, variazione organica naturale
      'FBM'                → Fractional Brownian Motion, simile ma più uniforme
      'RIDGED_MULTIFRACTAL'→ creste nette, ottimo per rocce e terrain
      'HYBRID_MULTIFRACTAL'→ via di mezzo
      'HETERO_TERRAIN'     → dettagli eterogeni, terrain realistico
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree
    tree.nodes.clear()
    out   = tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf  = tree.nodes.new('ShaderNodeBsdfPrincipled')
    noise = tree.nodes.new('ShaderNodeTexNoise')
    cramp = tree.nodes.new('ShaderNodeValToRGB')
    # Blender 5.x: noise_type è un enum sull'nodo
    try: noise.noise_type = noise_type
    except: pass
    noise.inputs['Scale'].default_value      = scale
    noise.inputs['Detail'].default_value     = 6.0
    noise.inputs['Roughness'].default_value  = 0.6
    noise.inputs['Distortion'].default_value = distortion
    cramp.color_ramp.elements[0].color = (*c1, 1.0)
    cramp.color_ramp.elements[1].color = (*c2, 1.0)
    tree.links.new(noise.outputs['Fac'],   cramp.inputs['Fac'])
    tree.links.new(cramp.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = roughness
    tree.links.new(bsdf.outputs['BSDF'],   out.inputs['Surface'])
    return m

# Esempi noise_type per materiali specifici:
# Calcestruzzo:  mat_noise("Concrete", (0.55,0.52,0.50), (0.38,0.35,0.32), roughness=0.90)
# Marmo bianco:  mat_noise("Marble", (0.95,0.94,0.92), (0.70,0.68,0.65), scale=14, distortion=0.6)
# Roccia:        mat_noise("Rock", (0.25,0.22,0.18), (0.12,0.10,0.08), noise_type='RIDGED_MULTIFRACTAL')
# Terreno:       mat_noise("Terrain", (0.18,0.14,0.08), (0.08,0.06,0.04), noise_type='HETERO_TERRAIN')
```

### Vetro
```python
def mat_glass(name="Glass", color=(0.8, 0.9, 1.0), roughness=0.02, ior=1.52):
    """
    Blender 5.x: Transmission Weight sostituisce Transmission.
    use_raytrace_refraction abilita rifrazione raytracing in EEVEE Next.
    surface_render_method = "BLENDED" per trasparenza corretta.
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree; tree.nodes.clear()
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    out  = tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value  = roughness
    # Transmission: Blender 4.x → "Transmission", 5.x → "Transmission Weight"
    for tname in ['Transmission Weight', 'Transmission']:
        if tname in [i.name for i in bsdf.inputs]:
            bsdf.inputs[tname].default_value = 1.0
            break
    if 'IOR' in [i.name for i in bsdf.inputs]:
        bsdf.inputs['IOR'].default_value = ior
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    # Blender 5.x: surface_render_method sostituisce blend_method
    try:
        m.surface_render_method = "BLENDED"
        m.use_raytrace_refraction = True   # rifrazione EEVEE Next
    except:
        m.blend_method = 'BLEND'
    return m

# Varianti vetro:
# Vetro chiaro:     mat_glass("VetroChiaro", (0.92,0.97,1.0), roughness=0.01, ior=1.52)
# Vetro verde:      mat_glass("VetroVerde",  (0.65,0.88,0.72), roughness=0.02, ior=1.52)
# Vetro smerigliato:mat_glass("VetroFrost",  (0.90,0.92,0.95), roughness=0.35, ior=1.47)
# Bottiglia vino:   mat_glass("BottleDark",  (0.04,0.18,0.06), roughness=0.03, ior=1.52)
```

### Metallo (acciaio, alluminio, rame, clearcoat)
```python
def mat_metal(name, color=(0.8, 0.8, 0.8), roughness=0.15, anisotropic=0.3,
              clearcoat=0.0):
    """
    roughness: 0.05=specchio, 0.15=spazzolato, 0.4=opaco
    clearcoat: 0.0=nessuno, 1.0=vernice lucida (auto, lacca)
    color:
      acciaio:  (0.80, 0.80, 0.82)
      alluminio:(0.91, 0.92, 0.93)
      rame:     (0.95, 0.64, 0.54)
      oro:      (1.00, 0.78, 0.34)
      cromo:    (0.95, 0.95, 0.96)

    Blender 5.x OpenPBR: Coat layer sostituisce il vecchio Clearcoat.
    Per metalli ad alta roughness usa distribution='MULTI_GGX' (più realistico).
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree; tree.nodes.clear()
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    out  = tree.nodes.new('ShaderNodeOutputMaterial')
    inp  = [i.name for i in bsdf.inputs]
    bsdf.inputs['Base Color'].default_value  = (*color, 1.0)
    bsdf.inputs['Metallic'].default_value    = 1.0
    bsdf.inputs['Roughness'].default_value   = roughness
    if 'Anisotropic' in inp:
        bsdf.inputs['Anisotropic'].default_value = anisotropic
    # Coat layer (Blender 5.x OpenPBR — clearcoat)
    if clearcoat > 0:
        if 'Coat Weight' in inp:        # Blender 5.x
            bsdf.inputs['Coat Weight'].default_value    = clearcoat
            bsdf.inputs['Coat Roughness'].default_value = 0.05
            bsdf.inputs['Coat IOR'].default_value       = 1.50
        elif 'Clearcoat' in inp:        # Blender 4.x
            bsdf.inputs['Clearcoat'].default_value          = clearcoat
            bsdf.inputs['Clearcoat Roughness'].default_value = 0.05
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m

# Esempi:
# mat_metal("Acciaio",    (0.80,0.80,0.82), roughness=0.15)
# mat_metal("Cromo",      (0.95,0.95,0.96), roughness=0.04)
# mat_metal("CarPaint",   (0.05,0.08,0.65), roughness=0.20, clearcoat=1.0)
# mat_metal("Oro",        (1.00,0.78,0.34), roughness=0.08, anisotropic=0.5)
```

### Subsurface scattering (pelle, cera, cibo, marmo)
```python
def mat_subsurface(name, color, subsurface_color=None, roughness=0.6,
                   radius=(1.0, 0.2, 0.1), scale=0.01, method='RANDOM_WALK'):
    """
    Subsurface scattering per materiali traslucenti.
    Blender 5.x OpenPBR: 'Subsurface Weight' + 'subsurface_method'.

    method:
      'RANDOM_WALK'      → pelle, cera, marmo (più preciso)
      'RANDOM_WALK_SKIN' → pelle umana con epidermide
      'BURLEY'           → veloce, meno preciso

    radius: (R, G, B) scattering — sangue/pelle: (1.0, 0.2, 0.1)
    scale:  0.005=pelle sottile, 0.02=cera, 0.05=marmo
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree; tree.nodes.clear()
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    out  = tree.nodes.new('ShaderNodeOutputMaterial')
    inp  = [i.name for i in bsdf.inputs]
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value  = roughness
    # Subsurface Weight (Blender 5.x) o Subsurface (4.x)
    for sname in ['Subsurface Weight', 'Subsurface']:
        if sname in inp:
            bsdf.inputs[sname].default_value = 0.8
            break
    if 'Subsurface Radius' in inp:
        bsdf.inputs['Subsurface Radius'].default_value = radius
    if 'Subsurface Scale' in inp:
        bsdf.inputs['Subsurface Scale'].default_value  = scale
    if subsurface_color and 'Subsurface Color' in inp:
        bsdf.inputs['Subsurface Color'].default_value  = (*subsurface_color, 1.0)
    # Metodo subsurface
    try: bsdf.subsurface_method = method
    except: pass
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m

# Esempi:
# mat_subsurface("Skin",  (0.84,0.61,0.50), method='RANDOM_WALK_SKIN', scale=0.006)
# mat_subsurface("Wax",   (0.98,0.94,0.82), method='RANDOM_WALK', scale=0.025)
# mat_subsurface("Marble",(0.94,0.92,0.90), method='RANDOM_WALK', radius=(0.8,0.6,0.5), scale=0.04)
```

### Tessuto / velluto (Sheen layer)
```python
def mat_fabric(name, color, roughness=0.85, sheen=0.8, sheen_tint=(1,1,1)):
    """
    Materiale tessuto con Sheen layer (Blender 5.x OpenPBR).
    Sheen dà l'effetto vellutato caratteristico dei tessuti.

    Blender 5.x: 'Sheen Weight' + 'Sheen Roughness' + 'Sheen Tint'
    Blender 4.x: 'Sheen' + 'Sheen Tint'
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree; tree.nodes.clear()
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    out  = tree.nodes.new('ShaderNodeOutputMaterial')
    inp  = [i.name for i in bsdf.inputs]
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value  = roughness
    # Sheen Weight (5.x) o Sheen (4.x)
    for sname in ['Sheen Weight', 'Sheen']:
        if sname in inp:
            bsdf.inputs[sname].default_value = sheen
            break
    if 'Sheen Roughness' in inp:
        bsdf.inputs['Sheen Roughness'].default_value = 0.5
    if 'Sheen Tint' in inp:
        bsdf.inputs['Sheen Tint'].default_value = (*sheen_tint, 1.0)
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m

# Esempi:
# mat_fabric("Velluto",  (0.08,0.04,0.25), roughness=0.95, sheen=0.9)
# mat_fabric("Lino",     (0.75,0.68,0.52), roughness=0.88, sheen=0.5)
# mat_fabric("Cotone",   (0.92,0.90,0.86), roughness=0.80, sheen=0.3)
```

### Legno (wave texture)
```python
def mat_wood(name, color=(0.45, 0.28, 0.12), scale=8, roughness=0.65):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree; tree.nodes.clear()
    out  = tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    wave = tree.nodes.new('ShaderNodeTexWave')
    bump = tree.nodes.new('ShaderNodeBump')
    cramp= tree.nodes.new('ShaderNodeValToRGB')
    wave.wave_type = 'BANDS'
    wave.inputs['Scale'].default_value      = scale
    wave.inputs['Distortion'].default_value = 2.5
    wave.inputs['Detail'].default_value     = 4.0
    c2 = tuple(min(1, c + 0.18) for c in color)
    cramp.color_ramp.elements[0].color = (*color, 1.0)
    cramp.color_ramp.elements[1].color = (*c2, 1.0)
    bump.inputs['Strength'].default_value = 0.3
    tree.links.new(wave.outputs['Color'],  cramp.inputs['Fac'])
    tree.links.new(wave.outputs['Color'],  bump.inputs['Height'])
    tree.links.new(cramp.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = roughness
    tree.links.new(bsdf.outputs['BSDF'],   out.inputs['Surface'])
    return m
```

### Blueprint (wireframe)
```python
def mat_blueprint(name, wire_color=(1.0,1.0,1.0),
                  face_color=(0.05,0.18,0.45), wire_size=0.0008):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; tree = m.node_tree; tree.nodes.clear()
    wire  = tree.nodes.new('ShaderNodeWireframe')
    wire.inputs['Size'].default_value = wire_size
    ew = tree.nodes.new('ShaderNodeEmission')
    ew.inputs['Color'].default_value    = (*wire_color, 1.0)
    ew.inputs['Strength'].default_value = 2.5
    ef = tree.nodes.new('ShaderNodeEmission')
    ef.inputs['Color'].default_value    = (*face_color, 1.0)
    ef.inputs['Strength'].default_value = 0.4
    mix = tree.nodes.new('ShaderNodeMixShader')
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    tree.links.new(wire.outputs['Fac'],        mix.inputs['Fac'])
    tree.links.new(ef.outputs['Emission'],     mix.inputs[1])
    tree.links.new(ew.outputs['Emission'],     mix.inputs[2])
    tree.links.new(mix.outputs['Shader'],      out.inputs['Surface'])
    return m
```

---

## CAMERA

### Set camera con preset
```python
def set_camera(preset='tre_quarti', target=(0,0,3), lens=None):
    presets = {
        'tre_quarti':   dict(loc=(-20,-20,12), rot=(55,0,-45), lens=35),
        'angolo':       dict(loc=(-15,-25,8),  rot=(52,0,-30), lens=28),
        'frontale':     dict(loc=(0,-30,5),    rot=(90,0,0),   lens=85),
        'aerial':       dict(loc=(0,0,40),     rot=(0,0,0),    lens=50),
        'street_level': dict(loc=(-8,-18,1.7), rot=(85,0,-20), lens=24),
        'interno':      dict(loc=(0,-3,1.6),   rot=(90,0,0),   lens=18),
        'product':      dict(loc=(4,-6,3),     rot=(70,0,35),  lens=85),
        'isometrica':   dict(loc=(20,-20,20),  rot=(54.7,0,45),lens=100),
    }
    p = presets.get(preset, presets['tre_quarti'])
    bpy.ops.object.camera_add(location=p['loc'])
    cam = bpy.context.active_object
    cam.name = f'Camera_{preset}'
    cam.rotation_euler = [math.radians(r) for r in p['rot']]
    cam.data.lens = lens or p['lens']
    bpy.ops.object.empty_add(location=target)
    tgt = bpy.context.active_object; tgt.name = 'CamTarget'
    tt = cam.constraints.new('TRACK_TO')
    tt.target = tgt; tt.track_axis = 'TRACK_NEGATIVE_Z'; tt.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam, tgt

def set_dof(cam, focus_distance=10.0, f_stop=2.8):
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = focus_distance
    cam.data.dof.aperture_fstop = f_stop
```

**Preset addizionali:**
| Preset | Uso |
|--------|-----|
| `product` | Oggetti singoli, prodotto su sfondo |
| `isometrica` | Vista assonometrica |
| `interno` | Grandangolo interni |
| `street_level` | Vista pedone / umana |

---

## ILLUMINAZIONE

### Tre punti (product / oggetti)
```python
def three_point_light(key_energy=800, fill_energy=200, rim_energy=500,
                      scale=1.0):
    """Setup luce classico per oggetti e prodotti."""
    # Key (principale, caldo)
    bpy.ops.object.light_add(type='AREA', location=(4*scale, -5*scale, 6*scale))
    key = bpy.context.active_object; key.name = "Key_Light"
    key.data.energy = key_energy; key.data.size = 2.0 * scale
    key.data.color  = (1.0, 0.95, 0.88)
    key.rotation_euler = (math.radians(50), 0, math.radians(40))

    # Fill (opposto, freddo)
    bpy.ops.object.light_add(type='AREA', location=(-5*scale, -3*scale, 4*scale))
    fill = bpy.context.active_object; fill.name = "Fill_Light"
    fill.data.energy = fill_energy; fill.data.size = 4.0 * scale
    fill.data.color  = (0.75, 0.85, 1.0)

    # Rim (retro, separazione)
    bpy.ops.object.light_add(type='AREA', location=(0, 6*scale, 5*scale))
    rim = bpy.context.active_object; rim.name = "Rim_Light"
    rim.data.energy = rim_energy; rim.data.size = 1.5 * scale
    rim.data.color  = (0.9, 0.95, 1.0)
    rim.rotation_euler = (math.radians(-40), 0, 0)
```

### Luce architetturale (sole + fill)
```python
def arch_lighting(sun_angle=(48, 0, 25), energy=5.0, color=(1.0,0.92,0.78)):
    bpy.ops.object.light_add(type='SUN', location=(10,-10,20))
    sun = bpy.context.active_object; sun.name = "Sun_Key"
    sun.data.energy = energy
    sun.data.color  = color
    sun.data.angle  = math.radians(3.0)
    sun.rotation_euler = tuple(math.radians(a) for a in sun_angle)
    # Fill sky
    bpy.ops.object.light_add(type='AREA', location=(-12, 5, 10))
    fill = bpy.context.active_object; fill.name = "Fill_Sky"
    fill.data.energy = 300; fill.data.size = 12.0
    fill.data.color  = (0.72, 0.82, 1.0)
    fill.rotation_euler = (math.radians(60), 0, math.radians(-120))
```

---

## ANIMAZIONI

### Turntable
```python
def anim_turntable(cx=0, cy=0, cz=0, radius=22, cam_height=10,
                   frames=250, lens=35):
    scene = bpy.context.scene
    scene.frame_start = 1; scene.frame_end = frames
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(cx, cy, cz))
    pivot = bpy.context.active_object; pivot.name = 'TT_Pivot'
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(cx, cy, cz+3))
    target = bpy.context.active_object; target.name = 'TT_Target'
    bpy.ops.object.camera_add(location=(cx+radius, cy, cz+cam_height))
    cam = bpy.context.active_object; cam.name = 'Camera_Turntable'
    cam.data.lens = lens; scene.camera = cam
    cam.parent = pivot; cam.location = (radius, 0, cam_height)
    tt = cam.constraints.new('TRACK_TO')
    tt.target = target; tt.track_axis = 'TRACK_NEGATIVE_Z'; tt.up_axis = 'UP_Y'
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert('rotation_euler', frame=1)
    pivot.rotation_euler = (0, 0, math.radians(360))
    pivot.keyframe_insert('rotation_euler', frame=frames)
    for fc in pivot.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.modifiers.new('CYCLES')
    return cam, pivot
```

### Flythrough
```python
def anim_flythrough(waypoints, frames=300, lens=28):
    scene = bpy.context.scene
    scene.frame_start = 1; scene.frame_end = frames
    bpy.ops.object.camera_add(location=waypoints[0][:3])
    cam = bpy.context.active_object; cam.name = 'Camera_Fly'; cam.data.lens = lens
    scene.camera = cam
    n = len(waypoints)
    for i, wp in enumerate(waypoints):
        fr = 1 + int(i * (frames-1) / max(n-1,1))
        cam.location = wp[:3]; cam.keyframe_insert('location', frame=fr)
        if len(wp) >= 6:
            d = Vector((wp[3]-wp[0], wp[4]-wp[1], wp[5]-wp[2]))
            cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
        cam.keyframe_insert('rotation_euler', frame=fr)
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
    return cam
```

---

## RENDER

### EEVEE (Blender 5.x — fast preview / produzione)
```python
def setup_render_eevee(w=1920, h=1080, samples=128):
    sc = bpy.context.scene
    try: sc.render.engine = "BLENDER_EEVEE_NEXT"
    except: sc.render.engine = "BLENDER_EEVEE"
    eevee = sc.eevee
    if hasattr(eevee, 'taa_render_samples'): eevee.taa_render_samples = samples
    if hasattr(eevee, 'use_shadows'):        eevee.use_shadows = True
    sc.render.resolution_x = w; sc.render.resolution_y = h
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look           = 'Medium High Contrast'
    sc.view_settings.exposure       = 0.2
    sc.render.use_compositing = False
```

### Cycles (fotorealistico)
```python
def setup_render_cycles(w=1920, h=1080, samples=256):
    sc = bpy.context.scene
    sc.render.engine        = 'CYCLES'
    sc.cycles.samples       = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x  = w; sc.render.resolution_y = h
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look           = 'Medium High Contrast'
```

---

## REGOLE QUALITÀ MODELING

1. **Bevel sempre** — ogni spigolo reale ha smussatura. Senza bevel: oggetto sembra plastica da videogioco anni '90.
2. **Smooth shading** su tutti i cilindri, sfere, forme curve. Flat shading solo su superfici intenzionalmente piatte (pannelli squadrati).
3. **Boolean per aperture** — finestre e porte vanno tagliate nel muro, non simulate con box adiacenti.
4. **Scale reali** — 1 BU = 1 metro. Un uomo: 1.75m. Porta: 2.1m×0.9m. Sedia: h=0.45m seduta, h=0.9m schienale.
5. **Topology pulita** — evita N-gon con più di 6 lati su superfici che ricevono SubSurf. Usa loop cuts per controllare la forma.
6. **Array per ripetizioni** — non duplicare manualmente elementi ripetuti (pali, finestre, gradini).
7. **Nomi significativi** — `Chair_Leg_FL` non `Cube.023`.
8. **Transform apply** — sempre dopo scale != (1,1,1) prima di Boolean o SubSurf.
9. **`ob.data.shade_smooth()` non `bpy.ops.object.shade_smooth()`** — l'operatore non funziona su mesh bmesh (lascia sharp_face=True → striature). Usa SEMPRE il metodo diretto sul mesh data-block. Verifica: `ob.data.normals_domain` deve essere `'POINT'`.
10. **ShaderNodeMixRGB è deprecato** — usa `ShaderNodeMix` con `data_type='RGBA'`, Color A = `inputs[6]`, Color B = `inputs[7]`, result = `outputs[2]`. MixRGB esiste ma restituisce giallo default — bug silenzioso!

---

## ANALISI RICHIESTA

Identifica da `$ARGUMENTS`:

| Keyword | Azione |
|---------|--------|
| `casa / villa / edificio` | Architettura con Boolean windows, railing, roof |
| `sedia / tavolo / mobile` | Furniture con bevel + smooth |
| `oggetto / prodotto / bottiglia` | make_lathe_object o product modeling |
| `auto / veicolo` | Body + wheels con smooth + bevel pesante |
| `blueprint / wireframe` | mat_blueprint su tutti gli oggetti |
| `camera [preset]` | set_camera(preset) |
| `turntable / orbita` | anim_turntable |
| `render / finale` | setup_render_eevee o cycles |
| `migliora / fix` | Visual loop: render → Read → analisi → correggi |

**Se richiesta ambigua → una sola domanda concisa, poi esegui.**

## Output

- Codice Python completo, nessun placeholder
- Usa sempre bevel + smooth shading sugli oggetti rilevanti
- Dopo esecuzione: render_and_read → Read → commenta cosa si vede → itera se necessario
- Scale reali (1 BU = 1 metro)
- Dopo salvataggio script: path + istruzioni `Blender > Scripting > Open > Run`
