---
description: >
  Skill di modellazione procedurale avanzata per Blender. Parallel Transport
  (anti-drift), loft da profili anatomici, Generalized Cylinder, eliche/DNA
  parametrici, Boolean per cavità interne, crescita differenziale.
  Propagazione matriciale M_{n+1}=M_n·T·R (Sez. 7), Vector Blending locale/globale,
  Tropismo, Perlin Noise Vector Field, Space Colonization (Sez. 10),
  State Machine Growth, Fillet Procedurale, rotation_difference() (Sez. 11),
  Plexus Effect, Delaunay, Voronoi, Kruskal MST (Sez. 12),
  Sistemi Ibridi Grafo+Cinematica (Sez. 13).
  Usa questa skill quando: l'oggetto ha una spine, la geometria nasce da sezioni
  trasversali, serve una struttura biologica, la forma cresce/si ramifica,
  o si parte da una nuvola di punti da connettere topologicamente.
allowed-tools:
  - Bash
  - Read
  - Write
  - mcp__Blender__execute_blender_code
  - mcp__Blender__get_screenshot_of_window_as_image
  - mcp__Blender__render_viewport_to_path
  - mcp__Blender__get_objects_summary
  - mcp__Blender__get_object_detail_summary
---

# Skill: Blender Procedural Modeling (Advanced)

Sei un esperto di modellazione procedurale matematica in Blender.
Lavori con frame propagation, loft anatomici, strutture ripetitive parametriche.

---

## Connessione — MCP (predefinito)

```python
# Esegui codice in Blender
mcp__Blender__execute_blender_code(code="""
import bpy, bmesh, math
from mathutils import Vector, Matrix
# ... codice ...
result = {"ok": True}
""")

# Screenshot rapido (no render)
mcp__Blender__get_screenshot_of_window_as_image()

# Render su file e poi Read per analisi visiva
mcp__Blender__render_viewport_to_path(output_path="C:/Users/josia/Downloads/preview.png")
```

---

## Visual Loop

```
1. execute_blender_code(build_code)
2. render_viewport_to_path("preview.png") → Read("preview.png") → analisi visiva
3. execute_blender_code(fix_code) → itera fino a soddisfazione
```

---

## IL PRINCIPIO FONDAMENTALE — Frame Propagation

Ogni punto su una curva ha un **frame locale** (sistema di riferimento):
- **T** (Tangent): direzione di avanzamento
- **N** (Normal): "su" del frame
- **B** (Binormal): B = T × N

Il problema del frame naïve (Frenet-Serret): N dipende dalla curvatura → **flipping**
su tratti rettilinei e **drift** su curve complesse.

**Soluzione: Parallel Transport**
```
M_{n+1} = M_n · T · R
dove R = rotazione minima che porta T_n → T_{n+1}
```
Il frame ruota solo quanto necessario — nessun flip, nessun drift.

```python
from mathutils import Vector, Matrix, Quaternion
import math

def parallel_transport(points):
    """
    Calcola un frame ortonormale per ogni punto della curva usando Parallel Transport.
    Elimina il flipping di Frenet-Serret su tratti rettilinei e curvi.
    
    Input : lista di Vector (punti della curva)
    Output: lista di (T, N, B) — tuple di Vector normalizzati
    """
    n = len(points)
    frames = [None] * n
    
    # Frame iniziale — scegli N0 perpendicolare a T0
    T0 = (points[1] - points[0]).normalized()
    # Trova un vettore non parallelo a T0
    up = Vector((0, 0, 1))
    if abs(T0.dot(up)) > 0.99:
        up = Vector((1, 0, 0))
    N0 = T0.cross(up).normalized()
    B0 = T0.cross(N0).normalized()
    frames[0] = (T0, N0, B0)
    
    for i in range(1, n):
        T_prev, N_prev, B_prev = frames[i - 1]
        if i < n - 1:
            T_curr = (points[i + 1] - points[i - 1]).normalized()
        else:
            T_curr = (points[i] - points[i - 1]).normalized()
        
        # Rotazione minima T_prev → T_curr (asse = T_prev × T_curr)
        axis = T_prev.cross(T_curr)
        if axis.length > 1e-8:
            axis.normalize()
            cos_a = max(-1.0, min(1.0, T_prev.dot(T_curr)))
            angle  = math.acos(cos_a)
            q = Quaternion(axis, angle)
            N_curr = q @ N_prev
            B_curr = T_curr.cross(N_curr).normalized()
            N_curr = B_curr.cross(T_curr).normalized()
        else:
            N_curr = N_prev.copy()
            B_curr = B_prev.copy()
        
        frames[i] = (T_curr, N_curr, B_curr)
    
    return frames

def reortho(T, N):
    """
    Riortonormalizza N rispetto a T (anti-drift).
    Chiama ogni 10-20 passi per evitare accumulo di errore floating point.
    """
    N = N - T * T.dot(N)
    if N.length < 1e-8:
        up = Vector((0,0,1)) if abs(T.z) < 0.99 else Vector((1,0,0))
        N = T.cross(up)
    return N.normalized()
```

---

## LOFT DA PROFILI — build_shell

Il loft connette anelli di vertici lungo una spine, creando superfici continue.
Usato per: cuori, vasi, colonne vertebrali, bottiglie a geometria variabile.

```python
import bpy, bmesh, math
from mathutils import Vector, Matrix

UNIT = 0.1  # 1 BU = 10 cm → misure in cm * UNIT

def gen_profile(rx, ry, segments=32, offset_x=0.0,
                bump_start=0, bump_end=0, bump_k=0.0):
    """
    Genera un anello ellittico con bump (usato per il ventricolo destro del cuore).
    
    rx, ry     : semi-assi ellisse [stessa unità di UNIT]
    offset_x   : spostamento laterale del centro
    bump_start/end : range angolare [°] dove applicare il bump
    bump_k     : intensità bump (0 = nessun bump)
    
    Ritorna: lista di Vector in piano XY centrati sull'origine
    """
    pts = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        deg   = math.degrees(angle) % 360
        x = rx * math.cos(angle)
        y = ry * math.sin(angle)
        if bump_k > 0 and bump_start < bump_end:
            if bump_start <= deg <= bump_end:
                t = (deg - bump_start) / (bump_end - bump_start)
                b = bump_k * math.sin(math.pi * t)
                x += b * math.cos(angle)
                y += b * math.sin(angle)
        pts.append(Vector((x + offset_x, y, 0)))
    return pts

def build_shell(frames_data, total_height, segments=32, name="Shell"):
    """
    Loft procedurale da una tabella di frame.
    
    frames_data : lista di tuple
                  (z_norm, rx, ry, offset_x, bump_start, bump_end, bump_k)
                  z_norm in [0,1], rx/ry in cm, altri parametri gen_profile
    total_height: altezza totale in cm
    segments    : divisioni angolari dell'anello
    
    Esempio (cuore):
        HEART_FRAMES = [
            (0.00, 0.6, 0.6, 0.0,   0,   0, 0.00),  # apice
            (0.54, 4.3, 3.1,-0.2, 180, 340, 0.43),  # diametro massimo
            (1.00, 1.0, 0.8, 0.0,   0,   0, 0.00),  # base
        ]
        build_shell(HEART_FRAMES, total_height=13.0)
    """
    bm = bmesh.new()
    rings = []
    
    for (z_norm, rx, ry, ox, bs, be, bk) in frames_data:
        z  = z_norm * total_height * UNIT
        rx_u = rx * UNIT
        ry_u = ry * UNIT
        ox_u = ox * UNIT
        ring_pts = gen_profile(rx_u, ry_u, segments, ox_u, bs, be, bk * UNIT)
        ring_verts = [bm.verts.new((p.x, p.y, z)) for p in ring_pts]
        rings.append(ring_verts)
    
    bm.verts.ensure_lookup_table()
    
    # Connetti anelli adiacenti con facce quad
    for ri in range(len(rings) - 1):
        r0, r1 = rings[ri], rings[ri + 1]
        for j in range(segments):
            nj = (j + 1) % segments
            bm.faces.new([r0[j], r0[nj], r1[nj], r1[j]])
    
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.shade_smooth()
    return obj

def loft_rings(bm, ring_a, ring_b):
    """
    Connette due anelli di BmVerts già esistenti nel bmesh.
    Utile per loft incrementale (aggiungere sezioni a un bmesh aperto).
    Entrambi gli anelli devono avere lo stesso numero di vertici.
    """
    n = len(ring_a)
    assert n == len(ring_b), "I due anelli devono avere lo stesso numero di vertici"
    for j in range(n):
        nj = (j + 1) % n
        bm.faces.new([ring_a[j], ring_a[nj], ring_b[nj], ring_b[j]])
```

---

## GENERALIZED CYLINDER — tubo lungo una curva

Un Generalized Cylinder è una sezione trasversale (qualunque forma) estrusa lungo
una spine, con il frame corretto a ogni punto grazie al Parallel Transport.

```python
def build_vessel(spine_points, radius=0.1, segments=12, name="Vessel",
                 taper=None):
    """
    Tubo (sezione circolare) lungo una curva 3D con Parallel Transport.
    
    spine_points : lista di Vector — la curva centrale
    radius       : raggio del tubo (o lista di raggi per taper)
    taper        : None = raggio costante
                   lista di float = raggio a ogni punto (len = len(spine_points))
    
    Usi tipici:
      Vasi sanguigni, arterie, colonna vertebrale, tubi idraulici, cavi
    
    Esempio:
        spine = [Vector((0,0,i*0.1)) for i in range(20)]
        # curva elicoidale:
        spine = [Vector((math.cos(i*0.3), math.sin(i*0.3), i*0.05)) for i in range(30)]
        build_vessel(spine, radius=0.02, segments=16, name="Aorta")
    """
    if len(spine_points) < 2:
        raise ValueError("Servono almeno 2 punti")
    
    radii = taper if taper is not None else [radius] * len(spine_points)
    frames = parallel_transport(spine_points)
    
    bm = bmesh.new()
    rings = []
    
    for i, (pt, (T, N, B), r) in enumerate(zip(spine_points, frames, radii)):
        ring = []
        for j in range(segments):
            angle = 2 * math.pi * j / segments
            offset = N * (r * math.cos(angle)) + B * (r * math.sin(angle))
            v = bm.verts.new(pt + offset)
            ring.append(v)
        rings.append(ring)
    
    bm.verts.ensure_lookup_table()
    for ri in range(len(rings) - 1):
        loft_rings(bm, rings[ri], rings[ri + 1])
    
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.shade_smooth()
    return obj


def build_vessel_custom_section(spine_points, section_pts_2d,
                                 frames=None, name="Vessel"):
    """
    Come build_vessel ma con sezione trasversale personalizzata (non solo cerchio).
    
    section_pts_2d : lista di (x, y) nel piano locale — il profilo della sezione
                     Esempio sezione ovale: [(r*cos(a), r*0.4*sin(a)) for a in ...]
                     Esempio sezione rettangolare: [(-w,-h),(w,-h),(w,h),(-w,h)]
    
    Utile per: manici, intestino, bronchi, sezioni rettangolari
    """
    if frames is None:
        frames = parallel_transport(spine_points)
    
    bm = bmesh.new()
    rings = []
    
    for pt, (T, N, B) in zip(spine_points, frames):
        ring = []
        for (sx, sy) in section_pts_2d:
            pos = pt + N * sx + B * sy
            ring.append(bm.verts.new(pos))
        rings.append(ring)
    
    bm.verts.ensure_lookup_table()
    for ri in range(len(rings) - 1):
        loft_rings(bm, rings[ri], rings[ri + 1])
    
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.shade_smooth()
    return obj
```

---

## ELICHE PARAMETRICHE — DNA e strutture ripetitive

```python
def helix_spine(n_steps, rise, twist_rad, radius, phase=0.0):
    """
    Genera i punti di una singola elica.
    
    rise      : salita per passo (es: 0.034 per B-DNA in unità Blender)
    twist_rad : rotazione per passo in radianti (es: math.radians(36) per B-DNA)
    radius    : distanza dall'asse centrale
    phase     : sfasamento angolare iniziale (es: math.pi per il secondo filamento)
    
    B-DNA parametri reali (×10 per visibilità Blender):
      rise=0.34, twist=math.radians(36), radius=1.0, 10 basi/giro
    
    Collagene tripla elica:
      rise=0.286, twist=math.radians(108), radius=0.46
    """
    return [
        Vector((
            radius * math.cos(i * twist_rad + phase),
            radius * math.sin(i * twist_rad + phase),
            i * rise
        ))
        for i in range(n_steps)
    ]

def double_helix(n_pairs=20, rise=0.34, twist=math.radians(36),
                 radius=1.0, strand_radius=0.08, name="DNA"):
    """
    Doppia elica completa con backbone e basi.
    Compatibile Blender 4.x/5.x (usa bmesh.ops.create_cone per i cilindri).
    
    FIX: bmesh.ops.create_cylinder NON esiste in Blender 4+/5+
         Usa create_cone con radius1 == radius2 per un cilindro.
    """
    strand1 = helix_spine(n_pairs, rise, twist, radius, phase=0.0)
    strand2 = helix_spine(n_pairs, rise, twist, radius, phase=math.pi)
    
    # Backbone filamento 1
    s1 = build_vessel(strand1, radius=strand_radius, segments=8, name=f"{name}_S1")
    # Backbone filamento 2
    s2 = build_vessel(strand2, radius=strand_radius, segments=8, name=f"{name}_S2")
    
    # Barre trasversali (coppie di basi)
    for i in range(n_pairs):
        p1, p2 = strand1[i], strand2[i]
        mid    = (p1 + p2) / 2
        length = (p2 - p1).length
        direction = (p2 - p1).normalized()
        
        # Orientamento del cilindro
        z_axis = Vector((0, 0, 1))
        q = z_axis.rotation_difference(direction)
        
        bpy.ops.mesh.primitive_cylinder_add(
            radius=strand_radius * 0.6,
            depth=length,
            location=mid
        )
        bar = bpy.context.active_object
        bar.name = f"{name}_Base_{i}"
        bar.rotation_euler = q.to_euler()
        bar.data.shade_smooth()
    
    return s1, s2
```

---

## BOOLEAN PER CAVITÀ INTERNE

Il pattern del cuore (Approccio C): shell esterna + Boolean DIFFERENCE per cavità.

**REGOLA CRITICA:** applica Subdivision PRIMA del Boolean, non dopo.
Il Boolean su mesh liscia produce bordi smooth. Il Boolean su mesh grezza produce
artefatti alle giunzioni che il SubSurf non può correggere.

```python
def add_cavity(shell_obj, center, rx, ry, rz, name="Cavity",
               solver='EXACT', apply=True):
    """
    Scava una cavità ellissoidale nella shell con Boolean DIFFERENCE.
    
    center     : Vector — centro della cavità in world space
    rx, ry, rz : semi-assi dell'ellissoide [BU]
    solver     : 'EXACT' (più preciso, più lento) o 'FAST'
    
    IMPORTANTE: shell_obj deve avere SubSurf già applicato (o livello ≥ 2)
                prima di chiamare questa funzione.
    
    Esempio (cuore — 4 camere):
        # Ventricolo Sinistro
        add_cavity(heart, Vector((0.02, 0, 0.04)), 0.025, 0.020, 0.045, "LV")
        # Ventricolo Destro
        add_cavity(heart, Vector((-0.02, 0.015, 0.04)), 0.016, 0.012, 0.038, "RV")
        # Atrio Sinistro
        add_cavity(heart, Vector((0.01, -0.01, 0.085)), 0.017, 0.013, 0.016, "LA")
        # Atrio Destro
        add_cavity(heart, Vector((-0.02, -0.01, 0.085)), 0.018, 0.015, 0.021, "RA")
    """
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, subdivisions=3,
                                           location=center)
    cutter = bpy.context.active_object
    cutter.name = f"{name}_Cutter"
    cutter.scale = (rx, ry, rz)
    bpy.ops.object.transform_apply(scale=True)
    
    bpy.context.view_layer.objects.active = shell_obj
    mod = shell_obj.modifiers.new(name, "BOOLEAN")
    mod.operation = 'DIFFERENCE'
    mod.object    = cutter
    mod.solver    = solver
    
    if apply:
        bpy.ops.object.modifier_apply(modifier=name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    
    return shell_obj

def assign_cavity_material(obj, cavity_mat, threshold_z=None):
    """
    Assegna materiale diverso alle facce interne (endocardio vs miocardio).
    Le facce interne si identificano per normale che punta verso l'interno
    (dot con vettore verso centro < 0) o per posizione Z se threshold_z fornito.
    
    Aggiunge cavity_mat allo slot 1 dell'oggetto.
    """
    if len(obj.material_slots) < 2:
        obj.data.materials.append(cavity_mat)
    else:
        obj.material_slots[1].material = cavity_mat
    
    center = Vector((0, 0, 0))
    bpy.context.view_layer.update()
    
    mesh = obj.data
    for poly in mesh.polygons:
        face_center = Vector(poly.center)
        face_normal = Vector(poly.normal)
        to_center   = (center - face_center).normalized()
        if threshold_z is not None:
            if face_center.z < threshold_z:
                poly.material_index = 1
        else:
            if face_normal.dot(to_center) > 0.3:
                poly.material_index = 1
```

---

## CRESCITA DIFFERENZIALE — superfici organiche

La crescita differenziale crea superfici corrugate/ondulate tipiche di foglie,
cortecce, intestino, cervello. Ogni vertice si sposta in base alla distanza
dai vicini vs. la sua distanza ideale.

```python
def differential_growth_step(obj, growth_rate=0.02, target_edge_len=None,
                              boundary_stiffness=0.8):
    """
    Un passo di crescita differenziale su una mesh.
    Chiama più volte (50-200 iterazioni) per ottenere la forma finale.
    
    growth_rate        : quanto crescono i vertici interni (0.01-0.05)
    target_edge_len    : lunghezza ideale degli edge (None = media attuale)
    boundary_stiffness : quanto i vertici di bordo resistono alla crescita [0-1]
    
    NOTA: richiedere sempre bpy.ops.object.modifier_apply su SubSurf PRIMA
    di applicare la crescita, altrimenti opera sulla mesh base e non su quella
    suddivisa.
    
    Workflow:
        1. Crea mesh di partenza (es: piano suddiviso 20x20)
        2. Seleziona e applica SubSurf livello 2
        3. Itera differential_growth_step 100-200 volte
        4. Il risultato è una superficie corrugata organica
    """
    import bmesh
    
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    if target_edge_len is None:
        total_len = sum(e.calc_length() for e in bm.edges)
        target_edge_len = total_len / len(bm.edges) if bm.edges else 0.1
    
    displacements = [Vector((0,0,0))] * len(bm.verts)
    
    for v in bm.verts:
        neighbors = [e.other_vert(v) for e in v.link_edges]
        if not neighbors:
            continue
        
        force = Vector((0, 0, 0))
        for nb in neighbors:
            vec  = nb.co - v.co
            dist = vec.length
            if dist < 1e-8:
                continue
            # Forza repulsiva se troppo vicini, attrattiva se troppo lontani
            diff  = dist - target_edge_len
            force += vec.normalized() * diff
        
        # I vertici di bordo crescono meno
        stiffness = boundary_stiffness if v.is_boundary else 1.0
        displacements[v.index] = force * growth_rate * stiffness
    
    for v in bm.verts:
        v.co += displacements[v.index]
    
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
```

---

## USARE lib/ DA blender_ragionamento

```python
# Carica la libreria nelle sessioni Blender
LIB_PATH = r"D:\blender_ragionamento"

import sys, importlib
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

import lib; importlib.reload(lib)

# Accesso alle funzioni
# lib.build_shell(lib.HEART_FRAMES, lib.HEART_TOTAL_HEIGHT_CM)
# lib.build_vessel([Vector(...)...], radius=0.02)
# lib.make_mat("Miocardio", color=(0.65, 0.05, 0.05))
# lib.cinematic_setup()
# lib.HEART_PARAMS   — dizionario misure ASE adulto
# lib.HEART_PARAMS_HYPERTROPHIC  — variante ipertrofica
# lib.HEART_PARAMS_DILATED       — variante dilatata
# lib.CUP_OUTER_FRAMES / CUP_INNER_FRAMES — tazza espresso
```

---

## PATTERN RICORRENTI

### Arteria coronaria (tubo su curva a S)
```python
# Spine a S per Left Anterior Descending (LAD)
spine = []
for i in range(40):
    t = i / 39
    x =  0.02 * math.sin(t * math.pi)
    y = -0.01 * math.sin(t * 2 * math.pi)
    z =  0.09 - t * 0.06
    spine.append(Vector((x, y, z)))

# Taper: si assottiglia verso la punta
radii = [0.003 * (1.0 - t * 0.6) for t in [i/39 for i in range(40)]]
build_vessel(spine, taper=radii, segments=10, name="Coronary_LAD")
```

### Colonna vertebrale (catena di corpi vertebrali)
```python
# Spine con curvatura lombare (lordosi)
def lumbar_spine(n_vertebrae=5, base_z=0.0):
    objects = []
    for i in range(n_vertebrae):
        t  = i / max(n_vertebrae - 1, 1)
        x  = 0.02 * math.sin(t * math.pi)       # lordosi lombare
        z  = base_z + i * 0.033                 # spaziatura 33mm
        h  = 0.025 * (1.0 - 0.1 * abs(t - 0.5)) # vertebre più alte al centro
        
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.022, depth=h, location=(x, 0, z))
        vb = bpy.context.active_object
        vb.name = f"L{i+1}_Vertebra"
        vb.data.shade_smooth()
        objects.append(vb)
    return objects
```

### DNA doppia elica in 3 righe
```python
import math
from mathutils import Vector
s1 = [Vector((math.cos(i*.628), math.sin(i*.628), i*.034)) for i in range(20)]
s2 = [Vector((-math.cos(i*.628), -math.sin(i*.628), i*.034)) for i in range(20)]
build_vessel(s1, radius=0.06, segments=8, name="Strand_1")
build_vessel(s2, radius=0.06, segments=8, name="Strand_2")
```

---

## REGOLE QUALITÀ

1. **Parallel Transport sempre** su catene di oggetti o tubi curvi —
   Frenet-Serret flippa. Usa `parallel_transport()` o Blender Curve con Tilt=0.

2. **SubSurf PRIMA del Boolean** — mai Boolean su mesh grezza, poi SubSurf.
   L'ordine corretto: mesh base → SubSurf (apply) → Boolean → materiali.

3. **`bmesh.ops.create_cone`** non `create_cylinder` — in Blender 4+/5+
   il cilindro bmesh si crea con `create_cone(radius1=r, radius2=r, ...)`.

4. **`obj.data.shade_smooth()`** non `bpy.ops.object.shade_smooth()` —
   l'operatore non rimuove `sharp_face` su mesh create con bmesh.

5. **UNIT = 0.1** (1 BU = 10 cm) per oggetti anatomici in cm.
   Per oggetti reali: misure in metri = 1 BU = 1 metro.

6. **Riortonormalizza** il frame ogni 20-50 passi con `reortho(T, N)`
   per evitare drift numerico su catene lunghe.

7. **Verifica geometria** dopo Boolean: `obj.data.validate()` ritorna True
   se ci sono errori. Usa solver='EXACT' per mesh biologiche complesse.

---

## CRESCITA COME PROPAGAZIONE MATRICIALE (Sezione 7)

Il metodo unificante di tutti i sistemi procedurali è la **propagazione locale per matrici**:
ogni elemento della catena (vertice, osso, vertebra, ramo) è definito come derivazione del precedente — mai in coordinate globali assolute.

### Notazione rigorosa

La formula vettoriale $\vec{P}_{n+1} = \vec{P}_n + \vec{V}$ è una semplificazione fuorviante: $\vec{V}$ deve essere espresso nella **base locale del passo n**. La forma corretta è:

$$M_{n+1} = M_n \cdot T(d) \cdot R(\alpha, \beta)$$

dove $T(d)$ è la traslazione e $R(\alpha, \beta)$ la rotazione — **entrambe in coordinate locali**.

```python
from mathutils import Vector, Matrix, Quaternion
import math

# Propagazione base: un passo lungo l'asse Z locale con rotazione angolare
def propagate_matrix(current_matrix, step_distance, alpha=0.0, beta=0.0):
    """
    Avanza di step_distance lungo l'asse Z locale, poi ruota di (alpha, beta).
    current_matrix: Matrix 4x4 del frame corrente
    alpha, beta:    rotazioni locali in radianti
    Ritorna: nuova Matrix 4x4
    """
    T = Matrix.Translation((0, 0, step_distance))
    Rx = Matrix.Rotation(alpha, 4, 'X')
    Ry = Matrix.Rotation(beta,  4, 'Y')
    return current_matrix @ T @ Rx @ Ry

# Riortonormalizzazione periodica (ogni 10-20 passi per evitare drift)
def reortho_matrix(m):
    """
    Resetta la precisione della base senza alterare l'orientamento.
    Equivalente a decomposizione QR implicita.
    """
    rot = m.to_3x3().normalized().to_4x4()
    rot.translation = m.translation
    return rot
```

### Variabilità parametrica

Con angoli **costanti** → eliche, spirali, frattali uniformi (sterili).
Con angoli **variabili** → strutture organiche:

| Sorgente della variazione | Struttura generata |
|---------------------------|--------------------|
| Noise 3D | Radici nodose, vasi sinuosi, rocce |
| Tabella antropometrica | Colonna vertebrale anatomica |
| L-System (regole di riscrittura) | Alberi, bronchi, vascolarizzazione |
| F-Curve Blender | Deformazioni guidate dalla fisica |

Il **primo passo** (seme/origine) determina l'intera forma per propagazione — essenza della modellazione parametrica.

### Connessione ai sistemi naturali

| Sistema | Parametro che varia | Struttura |
|---------|---------------------|-----------|
| Nautilus | Scala × 1.0618/giro | Spirale logaritmica |
| Colonna vertebrale | Angolo lordosi/cifosi per vertebra | Curva a S fisiologica |
| Albero | Angolo + lunghezza per livello | L-System |
| Vascolarizzazione | Diametro scalato per biforcazione | Legge di Murray |

---

## CRESCITA ORGANICA: DAL LOCALE AL GLOBALE (Sezione 10)

Il sistema $M_{n+1} = M_n \cdot T \cdot R$ è "cieco" rispetto al mondo circostante.
La soluzione è mescolare il calcolo locale con **influenze globali**.

### Vector Blending

$$\hat{D}_{finale} = \text{normalize}\left[(1 - W) \cdot \hat{L} + W \cdot \hat{G}\right]$$

- $\hat{L}$: direzione locale corrente (asse Z del frame)
- $\hat{G}$: influenza globale (gravità, attrattore, campo di rumore)
- $W \in [0,1]$: peso influenza globale (0 = locale puro, 1 = solo globale)

```python
from mathutils import Vector

def vector_blend_step(current_matrix, global_influence_fn, step_distance, W=0.3):
    """
    Un passo di crescita con blending locale-globale.
    global_influence_fn(pos) → Vector normalizzato (l'influenza globale)
    """
    pos = current_matrix.translation.copy()
    # Direzione locale: asse Z del frame corrente
    L = (current_matrix @ Vector((0, 0, 1)) - pos).normalized()
    # Influenza globale alla posizione corrente
    G = global_influence_fn(pos)
    # Blend
    D = ((1 - W) * L + W * G).normalized()
    return pos + D * step_distance
```

### A. Tropismo (Influenze Ambientali)

$\hat{G}$ è un vettore costante o funzione della posizione:

```python
# Gravitropismo: rami che si piegano verso il basso
def gravitropism(pos):
    return Vector((0, 0, -1))

# Fototropismo: crescita verso una sorgente di luce
def phototropism(pos, light_pos=Vector((0.5, 0, 2.0))):
    return (light_pos - pos).normalized()

# Tigmotropismo: la vite si avvicina al muro
def thigmotropism(pos, wall_pos=Vector((0.3, 0, 0))):
    return (wall_pos - pos).normalized()

# Repulsione ostacolo: radici che aggirano un sasso
def obstacle_repulsion(pos, obstacle_pos=Vector((0, 0, 0.05))):
    return (pos - obstacle_pos).normalized()
```

| Influenza | $\hat{G}$ | Effetto |
|-----------|-----------|---------|
| Gravità | $(0, 0, -1)$ | Salice piangente, radici nodose |
| Punto luce | $\text{norm}(P_{luce} - P_n)$ | Rami verso la finestra |
| Repulsione | $\text{norm}(P_n - P_{ostacolo})$ | Radici che aggirano un sasso |

### B. Perlin Noise Vector Field

Il rumore random per-angolo produce zig-zag innaturali.
Il Perlin Noise 3D produce curve fluide e continue:

```python
import mathutils.noise as mnoise
from mathutils import Vector

def get_noise_vector(pos, scale=1.0, seed=0):
    """
    Campiona un Vector Field di rumore Perlin alla posizione globale pos.
    Tre campionamenti sfasati danno le tre componenti del vettore.
    Poiché il rumore 3D è continuo, il risultato è sempre un arco fluido.
    """
    p = pos * scale
    vx = mnoise.noise(p + Vector((seed,     0, 0)))
    vy = mnoise.noise(p + Vector((seed + 1, 0, 0)))
    vz = mnoise.noise(p + Vector((seed + 2, 0, 0)))
    return Vector((vx, vy, vz)).normalized()

# Uso: vasi coronarici sinuosi
# G = get_noise_vector(pos, scale=3.0, seed=42)
# W = 0.25  → prevalentemente locale, leggermente ondulato
```

### C. Space Colonization Algorithm

Il più potente per strutture dendritiche (alberi vascolari, fulmini, spugne):

```
Pseudocodice:
  per ogni passo:
    per ogni meristema (punto di crescita attivo):
      attrattori_vicini = {a | |a - meristema| < R_influenza}
      se attrattori_vicini è vuoto → il ramo smette di crescere
      D = normalize(Σ normalize(a - meristema) per a in attrattori_vicini)
      nuovo_punto = meristema + D * step_length
      rimuovi attrattori con |a - nuovo_punto| < R_kill
```

**Risultato:** struttura che cresce in modo imprevedibile ma biologicamente sensato, riempiendo esattamente lo spazio degli attrattori — come capillari che raggiungono ogni cellula.

**Applicazione cardiaca:** distribuire 500 attrattori nel volume del miocardio, far partire 3 germogli (LAD, RCA, LCX) → Space Colonization produce automaticamente rami secondari e capillari.

### Formula unificata (Sezioni 7 + 10)

$$M_{n+1} = \text{look\_at}\left(\text{normalize}\left[(1-W) \cdot \hat{Z}_{M_n} + W \cdot \hat{G}(P_n)\right]\right) \cdot T(d)$$

Il Parallel Transport garantisce che la matrice risultante non accumuli torsioni spurie.

---

## STATE MACHINE GROWTH (Sezione 11)

Opposto al tropismo (continuo, senza memoria): qui il cambio di direzione è **discreto e condizionale**. L'algoritmo ha memoria (distanza accumulata) e agisce solo al superamento di una soglia.

| | Sezione 10 — Tropismo | Sezione 11 — State Machine |
|--|--|--|
| Cambio direzione | Continuo ad ogni passo | Discreto al superamento di soglia |
| Memoria | Nessuna | Sì (distanza accumulata) |
| Applicazione | Radici nodose, vasi sinuosi | Tubature, bambù, cavi, condotti |

### La Macchina a Stati

```
STATO 1 — Crescita Lineare
    → avanza di step_size lungo Z locale
    → incrementa distanza_accumulata
    → controlla: distanza_accumulata >= target?

TRIGGER → passa allo STATO 2

STATO 2 — Rotazione
    → calcola angolo tra Z_locale e nuova_direzione_globale
    → applica rotazione (immediata o distribuita = fillet)
    → reset distanza_accumulata = 0
    → passa allo STATO 1
```

Liste di waypoint: `[(5m, dir_X), (8m, dir_Z), (12m, dir_Y)]` — ad ogni trigger si aggiorna la direzione target.

### La matematica: `rotation_difference()`

```python
from mathutils import Vector, Matrix, Quaternion

def align_to_direction(current_matrix, new_direction_global):
    """
    Calcola e applica la rotazione minima per allineare Z locale a new_direction_global.
    rotation_difference() trova l'arco minimo — stesso principio del Parallel Transport
    ma per un cambio intenzionale (non per prevenire il flipping accidentale).
    """
    # Direzione locale attuale (asse Z della matrice corrente)
    z_locale = (current_matrix.to_3x3() @ Vector((0, 0, 1))).normalized()
    # Direzione target nello spazio globale
    nuova_dir = Vector(new_direction_global).normalized()
    # Quaternione di rotazione minima
    rot_quat = z_locale.rotation_difference(nuova_dir)
    # Applica alla matrice corrente
    return current_matrix @ rot_quat.to_matrix().to_4x4()
```

### Fillet Procedurale — raccordo dello spigolo vivo

Se la rotazione è immediata → angolo netto (tubature industriali).
Se distribuita su N passi → raccordo sferico (bambù, aorta, vertebre):

```python
def fillet_turn(current_matrix, new_direction, step_size, fillet_steps=8):
    """
    Distribuisce la rotazione verso new_direction su fillet_steps passi.
    Il raggio del raccordo è proporzionale a step_size * fillet_steps.
    """
    from mathutils import Vector, Quaternion
    z_loc = (current_matrix.to_3x3() @ Vector((0, 0, 1))).normalized()
    new_dir = Vector(new_direction).normalized()
    q_total = z_loc.rotation_difference(new_dir)
    # Slerp: angolo parziale a ogni passo
    angle_total = q_total.angle
    axis = q_total.axis if q_total.axis.length > 1e-8 else Vector((0, 0, 1))
    q_step = Quaternion(axis, angle_total / fillet_steps)
    matrices = []
    m = current_matrix.copy()
    for _ in range(fillet_steps):
        m = m @ q_step.to_matrix().to_4x4() @ Matrix.Translation((0, 0, step_size))
        matrices.append(m.copy())
    return matrices  # lista di frame intermedi per il loft
```

### Spettro discreto→continuo

```
Spigolo vivo              Raccordo procedurale        Tropismo continuo
(fillet_steps = 1)       (fillet_steps = N)          (W ad ogni passo)
       │                        │                            │
Tubatura industriale      Ramo di bambù              Radice organica
Condotto aerazione        Vertebra→vertebra          Coronaria sinuosa
```

| Struttura | Approccio | Parametri |
|-----------|-----------|-----------|
| Tubatura industriale | State Machine, steps=1 | lista waypoint + direzioni |
| Rami bambù | State Machine, steps=3-5 | lunghezza segmento, angolo nodo |
| Colonna vertebrale | State Machine + Fillet | angoli lordosi/cifosi per segmento |
| Aorta | State Machine + Fillet largo | 1-2 cambi dir., raggio ~30mm |
| Coronarie | Sezione 10 (Noise Field) | scala noise, W=0.2-0.4 |

---

## MODELLAZIONE A GRAFO (Sezione 12)

Paradigma opposto al cinematico: invece di un punto che viaggia, si parte da una **nuvola di punti già posizionati** e si decide *chi collegare a chi*.

| | Cinematico (Sez. 7-11) | A Grafo (Sez. 12) |
|--|--|--|
| Input | Un punto che si muove | Nuvola di punti |
| Output | Curva/tubo continuo | Rete, mesh, tessuto |
| Analogia | Pennello che disegna | Tessitore che annoda fili |

### 1. Plexus Effect — connessione per distanza soglia

```python
def plexus_effect(bm, verts, d_max):
    """
    Collega ogni coppia di vertici se la distanza è < d_max.
    Complessità O(N²) — per N grandi usare KD-tree.
    Applicazioni: reti neurali, molecole, ragnatele, motion graphics.
    """
    for i, va in enumerate(verts):
        for j, vb in enumerate(verts):
            if j <= i: continue
            if (va.co - vb.co).length < d_max:
                try: bm.edges.new((va, vb))
                except ValueError: pass  # arco già esistente
```

### 2. Triangolazione di Delaunay — dalla nuvola alla mesh

Costruisce automaticamente una mesh triangolata massimizzando l'angolo minimo di ogni triangolo. Nessun punto cade dentro la circonferenza circoscritta di nessun triangolo → mesh più regolare possibile.

```python
from scipy.spatial import Delaunay
import numpy as np

def delaunay_mesh(punti_3d, bm):
    """
    punti_3d: lista di Vector
    bm: bmesh già inizializzato
    Proietta su XY per Delaunay 2D, poi usa Z reale per i vertici.
    """
    points_2d = np.array([(v.x, v.y) for v in punti_3d])
    tri = Delaunay(points_2d)
    verts = [bm.verts.new(p) for p in punti_3d]
    for simplex in tri.simplices:
        try:
            bm.faces.new([verts[simplex[0]], verts[simplex[1]], verts[simplex[2]]])
        except ValueError: pass
```

Applicazioni: ricostruzione mesh da scansioni laser, terreni da punti quota, semplificazione mesh dense.

### 3. Diagrammi di Voronoi — l'inverso di Delaunay

Ogni cella contiene tutti i punti più vicini al suo "seme". I bordi delle celle Voronoi sono le mediatrici dei segmenti di Delaunay.

```python
from scipy.spatial import Voronoi
vor = Voronoi(points)
# vor.vertices       = vertici dei poligoni Voronoi
# vor.ridge_vertices = archi (bordi) tra celle
```

Applicazioni biologiche: scaglie di rettile, struttura trabecolare dell'osso, pattern cellulare della cornea, schiuma e bolle.

### 4. Minimum Spanning Tree (MST) — strutture ottimizzate

Algoritmo di Kruskal: trova il sottoinsieme minimo di archi che connette tutti i punti senza cicli, minimizzando la lunghezza totale.

```python
import heapq

def kruskal_mst(verts_list):
    """
    verts_list: lista di Vector
    Ritorna lista di coppie (i, j) degli archi del MST.
    Applicazioni: vene su foglie, ramificazioni fluviali, fulmini,
                 crepe su ceramica, struttura basilare vasi capillari.
    """
    edges = []
    n = len(verts_list)
    for i in range(n):
        for j in range(i + 1, n):
            d = (verts_list[i] - verts_list[j]).length
            heapq.heappush(edges, (d, i, j))
    parent = list(range(n))
    def find(x):
        while parent[x] != x: x = parent[x]
        return x
    mst = []
    while edges and len(mst) < n - 1:
        d, i, j = heapq.heappop(edges)
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
            mst.append((i, j))
    return mst
```

### Applicazioni nel progetto cardiaco

| Struttura | Algoritmo | Input | Output |
|-----------|-----------|-------|--------|
| Rete capillare miocardio | Plexus su attrattori ASE | Punti nel volume | Rete di capillari |
| Mesh da TAC | Delaunay 3D su contorni | Punti del contorno/slice | Mesh chiusa |
| Pattern trabecolare VD | Voronoi 3D | Semi randomici nel volume RV | Struttura spugnosa |
| Albero coronarico | MST | Attrattori nel miocardio | Vasi ottimizzati |

---

## SISTEMI IBRIDI: GRAFO + CINEMATICA (Sezione 13)

**Il Grafo pensa, la Cinematica costruisce.**

Il Grafo genera topologie perfette ma filiformi (zero spessore, non renderizzabili).
La Cinematica produce geometrie volumetriche ma fatica con topologie ramificate complesse.

### Schema del workflow ibrido

```
[ Dati Globali / Attrattori ]
           ↓
(Modellazione a Grafo — Sez. 12)
    Trova la Topologia (MST / Delaunay / Space Colonization)
           ↓
[ Scheletro Logico: Nodi e Archi ]
           ↓
(Modellazione Cinematica — Sez. 7-11)
    Sweep/Loft lungo gli archi (State Machine + Fillet)
    Parallel Transport per orientare i profili
    Legge di Murray per scalare i raggi alle biforcazioni
           ↓
[ Mesh Volumetrica 3D Finale ]
```

### Applicazione: albero coronarico completo

```python
# Fase 1 (Grafo): scheletro astratto
# 1. Genera attrattori sulla superficie del miocardio (proporzioni ASE)
# 2. Space Colonization → grafo di ramificazione da radice aortica
# 3. MST per determinare albero ottimale

# Fase 2 (Ibrido): trasforma archi in waypoint ordinati
# (ogni arco grafo → lista di punti intermedi per state_machine_path)

# Fase 3 (Cinematica): costruzione volumetrica
# - state_machine_path() inserisce raccordi ai cambi di direzione
# - build_vessel() genera il tubo con Parallel Transport
# - radius_bu diminuisce man mano che ci si allontana dalla radice (Legge di Murray)

# Legge di Murray per vasi sanguigni:
# r_parent^3 = r_child1^3 + r_child2^3
def murray_radius(r_parent, ratio=0.5):
    """Raggio figlio per biforcazione simmetrica."""
    return r_parent * (0.5 ** (1/3))  # ≈ r_parent * 0.794
```

**Sintesi:** il Grafo decide il "Dove" e il "Come è connesso", la Cinematica decide il "Che forma ha" e il "Quanto è spesso".

---

## ANALISI RICHIESTA

| Keyword | Tecnica |
|---------|---------|
| `cuore / vaso / arteria / vena` | build_shell + add_cavity + build_vessel |
| `DNA / elica / collagene` | double_helix / helix_spine + build_vessel |
| `colonna / vertebra / spine` | lumbar_spine + parallel_transport |
| `tubo / pipe / cavo su curva` | build_vessel |
| `sezione personalizzata / manico ovale` | build_vessel_custom_section |
| `crescita / organico / corrugato` | differential_growth_step (iterato) |
| `cavità / camera / vuoto interno` | add_cavity + assign_cavity_material |
| `lib / blender_ragionamento` | Carica con sys.path + importlib.reload |
| `propagazione matriciale / L-system / vertebra` | propagate_matrix + reortho_matrix (Sez. 7) |
| `tropismo / gravitropismo / fototropismo / vite` | vector_blend_step + influenza_fn (Sez. 10) |
| `rumore organico / sinuoso / corona sinuosa` | get_noise_vector con mathutils.noise (Sez. 10) |
| `space colonization / albero vascolare` | Space Colonization pseudocode (Sez. 10) |
| `state machine / bambù / tubatura / waypoint` | align_to_direction + fillet_turn (Sez. 11) |
| `plexus / rete neurale / ragnatela` | plexus_effect (Sez. 12) |
| `delaunay / mesh da punti / scansione` | delaunay_mesh con scipy (Sez. 12) |
| `voronoi / scaglie / trabecolare / bolle` | scipy.spatial.Voronoi (Sez. 12) |
| `minimum spanning tree / vene foglia / fulmini` | kruskal_mst (Sez. 12) |
| `grafo + loft / albero coronarico completo` | Workflow ibrido Grafo→Cinematica (Sez. 13) |

**Se richiesta ambigua → chiedi: "La forma ha una spine (asse principale)?
Ha profili variabili lungo quell'asse? Ha influenze globali (gravità, attrattori)?
Oppure parte da una nuvola di punti da connettere (grafo)?"**

## Output

- Codice Python completo, nessun placeholder
- Usa sempre parallel_transport per tubi su curva (non Frenet-Serret)
- Dopo esecuzione: render → Read → analisi visiva → itera
- Commenta le misure anatomiche con fonte (ASE, Gray's Anatomy, ecc.)
