---
description: >
  Skill di sculpting procedurale per Blender. Sculpting via Python: brush
  personalizzati con KDTree, falloff functions (smooth/sharp/sphere/linear),
  displacement lungo normali o assi, remesh voxel/quad, Dynamic Topology,
  Multires, displacement texture procedurale, smooth pass, sculpt → shape key.
  Usa questa skill quando: la forma deve essere organica/irregolare, ha dettagli
  di superficie (pori, rughe, dents, rilievi), o parte da una primitiva che
  va deformata artisticamente invece che costruita pezzo per pezzo.
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

# Skill: Blender Sculpting (Procedurale)

Sei un esperto di sculpting 3D in Blender via Python.
Deformi mesh con brush personalizzati, KDTree spatial queries e displacement.

---

## Connessione — MCP (predefinito)

```python
mcp__Blender__execute_blender_code(code="""
import bpy, bmesh, math
from mathutils import Vector
from mathutils.kdtree import KDTree
# ... codice ...
result = {"ok": True}
""")

mcp__Blender__get_screenshot_of_window_as_image()
mcp__Blender__render_viewport_to_path(output_path="C:/Users/josia/Downloads/sculpt.png")
```

---

## Visual Loop

```
1. execute_blender_code(mesh_base_code)       ← crea primitiva + remesh
2. execute_blender_code(sculpt_code)          ← applica brush
3. get_screenshot_of_window_as_image()        ← analisi rapida viewport
4. execute_blender_code(fix_code)             ← raffina → itera
5. render_viewport_to_path("final.png")       ← render finale
```

---

## IL PRINCIPIO — Sculpting Procedurale vs. Sculpt Mode

Blender ha due approcci:

| | Sculpt Mode (operatori) | Sculpting Procedurale (Python) |
|-|------------------------|-------------------------------|
| Controllo | Limitato da Claude | Totale — ogni vertice |
| Riproducibilità | No | Sì — deterministico |
| Falloff | Preset fissi | Personalizzabile |
| Spatial query | Manuale | KDTree O(log n) |
| Iterabilità | Difficile | Facile |

**Usa Sculpt Mode** solo per operazioni globali (remesh, smooth, dyntopo setup).
**Usa Python** per tutto il resto — brush, displacement, deformazioni specifiche.

---

## SETUP MESH — Prima di Sculpting

La mesh di partenza determina la qualità del risultato.
Regola: **più poligoni = più dettaglio**, ma con costo. Bilanciare sempre.

```python
import bpy, math

def sculpt_base_sphere(name="SculptObj", radius=0.12,
                        segments=64, rings=48):
    """
    Sfera UV — punto di partenza ottimale per oggetti organici.
    segments=64, rings=48 → ~6000 vertici, buon punto di partenza.
    Dopo: applica remesh o subdivide per più dettaglio.
    
    IMPORTANTE: usa shade_smooth() e origin_to_geometry subito.
    """
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, segments=segments, ring_count=rings,
        location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.shade_smooth()
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    result = {'verts': len(obj.data.vertices), 'name': obj.name}
    return obj

def sculpt_base_cube(name="SculptBox", size=0.2, cuts=8):
    """
    Cubo suddiviso — per sculpting di forme angolari/rocciose.
    cuts=8 → ~4000 facce. Aumenta per più dettaglio.
    """
    bpy.ops.mesh.primitive_cube_add(size=size, location=(0,0,0))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.shade_smooth()
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    return obj
```

---

## REMESH — Topologia uniforme pre-sculpt

Il remesh crea una topologia uniforme (tutti i poligoni della stessa dimensione)
— fondamentale per sculpting uniforme senza artefatti.

```python
def remesh_voxel(obj, voxel_size=0.005, adaptivity=0.0):
    """
    Remesh voxelico — il più semplice e robusto.
    Crea topologia quad uniforme da qualsiasi mesh.
    
    voxel_size: dimensione del voxel [BU]
      0.010 → ~2000 facce (preview rapido)
      0.005 → ~8000 facce (sculpting base)
      0.002 → ~50000 facce (sculpting dettagliato)
      0.001 → ~200000 facce (sculpting fine — lento!)
    
    adaptivity: 0=completamente uniforme, 0.5=adattivo (meno facce sulle piatte)
    
    NOTA: distrugge UV, materiali per slot, vertex groups — fallo PRIMA
    di aggiungere materiali o weight groups.
    """
    bpy.context.view_layer.objects.active = obj
    
    mod = obj.modifiers.new("Remesh", "REMESH")
    mod.mode       = 'VOXEL'
    mod.voxel_size = voxel_size
    mod.adaptivity = adaptivity
    mod.use_smooth_shade = True
    
    bpy.ops.object.modifier_apply(modifier="Remesh")
    obj.data.shade_smooth()
    return obj

def remesh_quad(obj, depth=6):
    """
    Remesh Quad (Instant Meshes-style) — crea quad ordinati.
    depth: 4=bassa (pochi poligoni), 6=media, 8=alta
    
    Meno usato del voxel perché più lento e meno prevedibile.
    """
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("Remesh", "REMESH")
    mod.mode  = 'SHARP'
    mod.octree_depth = depth
    mod.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier="Remesh")
    return obj

def subdivide_smooth(obj, levels=2):
    """
    SubSurf applicato — alternativa al remesh per mesh già ben topologizzate.
    Usato per aggiungere risoluzione a una mesh bmesh costruita a mano.
    levels=2 → ×4 vertici, levels=3 → ×16 vertici
    """
    mod = obj.modifiers.new("Subdivision", "SUBSURF")
    mod.levels        = levels
    mod.render_levels = levels
    mod.subdivision_type = 'CATMULL_CLARK'
    bpy.ops.object.modifier_apply(modifier="Subdivision")
    obj.data.shade_smooth()
    return obj
```

---

## KDTREE — Spatial Query

Il KDTree è la struttura dati centrale per il sculpting procedurale.
Dato un punto nello spazio, trova in O(log n) tutti i vertici entro un raggio.

```python
from mathutils import Vector
from mathutils.kdtree import KDTree

def build_kd(obj):
    """
    Costruisce un KDTree dai vertici di obj in world space.
    
    IMPORTANTE: chiama bpy.context.view_layer.update() prima se l'oggetto
    è stato modificato di recente (matrix_world potrebbe essere stale).
    
    Ritorna: (kd, world_verts) — il KD-tree e la lista di posizioni world
    """
    bpy.context.view_layer.update()
    mw = obj.matrix_world
    wv = [mw @ v.co for v in obj.data.vertices]
    kd = KDTree(len(wv))
    for i, v in enumerate(wv):
        kd.insert(v, i)
    kd.balance()
    return kd, wv

# Uso:
# kd, wv = build_kd(obj)
# hits = kd.find_range(Vector((0, 0, 0.12)), 0.04)
# for world_pos, vertex_index, distance in hits:
#     v = obj.data.vertices[vertex_index]
#     # ... modifica v.co ...
```

---

## FALLOFF FUNCTIONS

Il falloff determina come l'influenza del brush decresce dalla distanza:

```python
def fo_smooth(d, r):
    """Smoothstep — transizione morbida. Default per la maggior parte dei brush."""
    t = min(d / r, 1.0)
    return 1.0 - (3*t*t - 2*t*t*t)

def fo_sharp(d, r):
    """Cubica inversa — picco acuto al centro, cade rapidamente. Per dents e dimples."""
    t = min(d / r, 1.0)
    return (1.0 - t) ** 3

def fo_sphere(d, r):
    """Semicircolare — deformazione a cupola. Per bump e rigonfiamenti."""
    t = min(d / r, 1.0)
    return math.sqrt(max(0.0, 1.0 - t*t))

def fo_linear(d, r):
    """Lineare — cono perfetto. Per creste e spine."""
    return max(0.0, 1.0 - d / r)

def fo_constant(d, r):
    """Costante — tutto al massimo nel raggio, 0 fuori. Per tagli netti."""
    return 1.0 if d < r else 0.0

FALLOFFS = {
    'smooth':   fo_smooth,
    'sharp':    fo_sharp,
    'sphere':   fo_sphere,
    'linear':   fo_linear,
    'constant': fo_constant,
}
```

---

## BRUSH — Il motore centrale

```python
def brush(obj, center, radius, strength,
          direction='normal', falloff='smooth',
          mask_fn=None):
    """
    Brush procedurale universale — la funzione più importante della skill.
    
    center    : Vector o tuple (x,y,z) in WORLD SPACE — centro del brush
    radius    : raggio di influenza [BU]
    strength  : intensità dello spostamento [BU] (positivo=fuori, negativo=dentro)
    
    direction : come si spostano i vertici
      'normal'    → lungo la normale locale del vertice (inflate/deflate)
      'z'         → lungo l'asse Z world (flatten verso l'alto/basso)
      '-z'        → verso il basso
      'smooth'    → media con i vicini (smooth pass)
      Vector((x,y,z)) → direzione arbitraria in world space
    
    falloff   : 'smooth' | 'sharp' | 'sphere' | 'linear' | 'constant'
    
    mask_fn   : funzione(vertex_co_world) → float [0,1]
                usata per mascherare aree (es: solo la parte superiore)
                None = nessuna maschera
    
    Ritorna: numero di vertici modificati
    
    ESEMPI:
      # Dimple in cima (come mela, albicocca)
      brush(obj, (0,0,0.12), radius=0.045, strength=-0.028,
            direction='normal', falloff='sharp')
      
      # Base appiattita
      brush(obj, (0,0,-0.12), radius=0.055, strength=-0.018,
            direction='z', falloff='sphere')
      
      # Bump equatoriale
      brush(obj, (0.12,0,0), radius=0.07, strength=0.008,
            direction='normal', falloff='smooth')
      
      # Ruga (cresta lineare)
      brush(obj, (0,0,0.05), radius=0.02, strength=0.005,
            direction='normal', falloff='sharp')
    """
    mw  = obj.matrix_world
    mwi = mw.inverted()
    nm  = mwi.transposed().to_3x3()   # per trasformare le normali
    
    fn  = FALLOFFS.get(falloff, fo_smooth)
    kd, _ = build_kd(obj)
    center_v = Vector(center)
    
    hits = kd.find_range(center_v, radius)
    if not hits:
        return 0
    
    for world_pos, vi, dist in hits:
        v = obj.data.vertices[vi]
        w = fn(dist, radius)
        
        # Maschera opzionale
        if mask_fn is not None:
            w *= mask_fn(world_pos)
        
        if w < 1e-4:
            continue
        
        # Calcola direzione di spostamento
        if direction == 'normal':
            d_world = (nm @ v.normal).normalized() * strength * w
        elif direction == 'z':
            d_world = Vector((0, 0, strength * w))
        elif direction == '-z':
            d_world = Vector((0, 0, -abs(strength) * w))
        elif direction == 'smooth':
            # Media con i vicini (smooth pass locale)
            neighbors = [obj.data.vertices[e.other_vert(v).index].co
                         for e in v.link_edges]
            if neighbors:
                avg = sum(neighbors, Vector()) / len(neighbors)
                d_local = (avg - v.co) * w * abs(strength) * 10
                v.co += d_local
            continue
        else:
            d_world = Vector(direction).normalized() * strength * w
        
        # Trasforma da world a local e applica
        v.co += mwi.to_3x3() @ d_world
    
    obj.data.update()
    return len(hits)


def smooth_pass(obj, center, radius, strength=0.5, iterations=1):
    """
    Smooth pass localizzato — attenua rughe/artefatti in un'area.
    Chiama più volte per smooth progressivo.
    
    strength: 0=nessun effetto, 1=media completa con i vicini
    """
    kd, _ = build_kd(obj)
    center_v = Vector(center)
    fn = fo_smooth
    
    for _ in range(iterations):
        hits = kd.find_range(center_v, radius)
        displacements = {}
        
        for _, vi, dist in hits:
            v = obj.data.vertices[vi]
            w = fn(dist, radius) * strength
            neighbors = [obj.data.vertices[e.other_vert(v).index].co
                         for e in v.link_edges]
            if neighbors:
                avg = sum(neighbors, Vector()) / len(neighbors)
                displacements[vi] = (avg - v.co) * w
        
        for vi, delta in displacements.items():
            obj.data.vertices[vi].co += delta
        
        obj.data.update()
        kd, _ = build_kd(obj)  # rebuild dopo modifica
    
    return len(hits) if hits else 0


def global_smooth(obj, strength=0.3, iterations=2):
    """
    Smooth globale su tutta la mesh.
    Utile dopo displacement texture o sculpt aggressivo.
    """
    for _ in range(iterations):
        for v in obj.data.vertices:
            neighbors = [obj.data.vertices[e.other_vert(v).index].co
                         for e in v.link_edges]
            if neighbors:
                avg = sum(neighbors, Vector()) / len(neighbors)
                v.co += (avg - v.co) * strength
        obj.data.update()
```

---

## DISPLACEMENT TEXTURE — Dettaglio procedurale

```python
import math, random

def noise3d(x, y, z, seed=0, octaves=4, persistence=0.5, lacunarity=2.0):
    """
    Noise 3D approssimato (puro Python, senza dipendenze).
    Usa per displacement, rughe, variazioni di superficie.
    
    octaves     : 1=liscio, 4=medio, 8=molto dettagliato
    persistence : quanto ogni ottava diminuisce (0.5=standard)
    lacunarity  : quanto ogni ottava aumenta di frequenza (2.0=standard)
    
    Ritorna: float in circa [-1, 1]
    """
    rng = random.Random(seed)
    offsets = [(rng.uniform(-100,100), rng.uniform(-100,100),
                rng.uniform(-100,100)) for _ in range(octaves)]
    
    val = 0.0
    amp = 1.0
    freq = 1.0
    max_val = 0.0
    
    for ox, oy, oz in offsets:
        # Lattice noise approssimato (hash di coordinate)
        xi = int(math.floor((x + ox) * freq))
        yi = int(math.floor((y + oy) * freq))
        zi = int(math.floor((z + oz) * freq))
        
        def h(a, b, c):
            return ((a * 1619 + b * 31337 + c * 6971 + seed * 1013) & 0x7fffffff) / 0x7fffffff
        
        # Trilinear interpolation
        fx = (x + ox) * freq - math.floor((x + ox) * freq)
        fy = (y + oy) * freq - math.floor((y + oy) * freq)
        fz = (z + oz) * freq - math.floor((z + oz) * freq)
        
        # Smoothstep
        ux = fx*fx*(3-2*fx); uy = fy*fy*(3-2*fy); uz = fz*fz*(3-2*fz)
        
        n = (h(xi,yi,zi)*(1-ux)*(1-uy)*(1-uz) + h(xi+1,yi,zi)*ux*(1-uy)*(1-uz) +
             h(xi,yi+1,zi)*(1-ux)*uy*(1-uz) + h(xi+1,yi+1,zi)*ux*uy*(1-uz) +
             h(xi,yi,zi+1)*(1-ux)*(1-uy)*uz + h(xi+1,yi,zi+1)*ux*(1-uy)*uz +
             h(xi,yi+1,zi+1)*(1-ux)*uy*uz + h(xi+1,yi+1,zi+1)*ux*uy*uz)
        
        val += (n * 2 - 1) * amp
        max_val += amp
        amp  *= persistence
        freq *= lacunarity
    
    return val / max_val if max_val > 0 else 0.0


def displace_noise(obj, scale=8.0, strength=0.005, seed=42,
                   octaves=4, direction='normal'):
    """
    Applica displacement noise su tutta la mesh.
    
    scale    : frequenza del noise (2=grossolano, 8=medio, 20=fine come pori)
    strength : ampiezza del displacement [BU]
    direction: 'normal' (lungo normali) o 'z' (solo verticale)
    
    Usi tipici:
      Pelle/frutta:  scale=10, strength=0.003, octaves=5
      Roccia:        scale=4,  strength=0.015, octaves=6
      Legno:         scale=8,  strength=0.006, octaves=3
      Tessuto:       scale=20, strength=0.002, octaves=2
    """
    mw  = obj.matrix_world
    mwi = mw.inverted()
    nm  = mwi.transposed().to_3x3()
    
    for v in obj.data.vertices:
        wp = mw @ v.co
        n  = noise3d(wp.x * scale, wp.y * scale, wp.z * scale,
                     seed=seed, octaves=octaves)
        
        if direction == 'normal':
            d_world = (nm @ v.normal).normalized() * n * strength
        else:  # 'z'
            d_world = Vector((0, 0, n * strength))
        
        v.co += mwi.to_3x3() @ d_world
    
    obj.data.update()


def displace_wave(obj, axis='z', wavelength=0.05, amplitude=0.003,
                  phase=0.0):
    """
    Displacement ondulatorio periodico — per rughe parallele, squame, tessuto.
    
    axis       : 'x', 'y', 'z' — direzione delle onde
    wavelength : distanza tra due creste [BU]
    amplitude  : altezza delle creste [BU]
    
    Usi tipici:
      Rughe su fronte:   axis='z', wavelength=0.012, amplitude=0.002
      Squame di pesce:   axis='x', wavelength=0.008, amplitude=0.004
      Trama tessuto:     axis='y', wavelength=0.005, amplitude=0.001
    """
    mw  = obj.matrix_world
    mwi = mw.inverted()
    nm  = mwi.transposed().to_3x3()
    ax  = {'x': 0, 'y': 1, 'z': 2}[axis]
    
    for v in obj.data.vertices:
        wp = mw @ v.co
        t  = math.sin(wp[ax] * 2 * math.pi / wavelength + phase)
        d_world = (nm @ v.normal).normalized() * t * amplitude
        v.co += mwi.to_3x3() @ d_world
    
    obj.data.update()
```

---

## DEFORMAZIONI GLOBALI — Schiacciamento, torsione, bend

```python
def flatten_axis(obj, axis='z', factor=0.85):
    """
    Schiaccia l'oggetto lungo un asse (factor < 1 = più piatto).
    Tipico: mela (z*0.88), arancio (z*0.92), disco (z*0.3)
    """
    ax = {'x': 0, 'y': 1, 'z': 2}[axis]
    for v in obj.data.vertices:
        v.co[ax] *= factor
    obj.data.update()

def pinch(obj, center, radius, strength=0.3, axis=None):
    """
    Pinch: attrae i vertici verso il centro del brush.
    Opposto di Inflate. Utile per: pupilla, bocca chiusa, orecchio elfico.
    
    axis: None=pinch 3D, 'z'=pinch solo laterale (mantiene altezza)
    """
    kd, _ = build_kd(obj)
    mw  = obj.matrix_world
    mwi = mw.inverted()
    center_w = Vector(center)
    
    for _, vi, dist in kd.find_range(center_w, radius):
        v = obj.data.vertices[vi]
        wp = mw @ v.co
        w  = fo_smooth(dist, radius) * strength
        direction = (center_w - wp)
        if axis == 'z':
            direction.z = 0
        if direction.length > 1e-6:
            v.co += mwi.to_3x3() @ (direction.normalized() * w * dist)
    
    obj.data.update()

def crease(obj, start, end, width=0.01, depth=0.008, falloff='sharp'):
    """
    Crea una ruga/piega lineare tra due punti.
    
    start, end : Vector — estremi della piega in world space
    width      : larghezza della piega [BU]
    depth      : profondità [BU] (positivo=fuori, negativo=dentro)
    
    Usi: rughe su viso, cuciture su cuoio, nervature su foglia
    """
    mw  = obj.matrix_world
    mwi = mw.inverted()
    nm  = mwi.transposed().to_3x3()
    fn  = FALLOFFS.get(falloff, fo_sharp)
    
    start_v = Vector(start)
    end_v   = Vector(end)
    seg     = end_v - start_v
    seg_len = seg.length
    
    if seg_len < 1e-8:
        return
    
    seg_n = seg / seg_len
    
    for v in obj.data.vertices:
        wp  = mw @ v.co
        # Distanza dal punto di proiezione sul segmento
        t   = max(0.0, min(1.0, (wp - start_v).dot(seg_n) / seg_len))
        proj = start_v + seg_n * t * seg_len
        dist = (wp - proj).length
        
        w = fn(dist, width)
        if w < 1e-4:
            continue
        
        d_world = (nm @ v.normal).normalized() * depth * w
        v.co += mwi.to_3x3() @ d_world
    
    obj.data.update()
```

---

## DYNAMIC TOPOLOGY — Dyntopo

Il Dyntopo suddivide/unisce gli edge durante lo sculpt per mantenere
la densità di poligoni uniforme. Utile solo con bpy.ops sculpt mode.

```python
def enable_dyntopo(obj, detail_size=12, method='RELATIVE', constant_detail=6):
    """
    Abilita Dynamic Topology per sculpting adattivo.
    
    detail_size     : risoluzione relativa (più basso = più dettaglio)
    method          : 'RELATIVE' (adattivo alla vista) o 'CONSTANT' (fisso)
    constant_detail : risoluzione per CONSTANT (facce/cm²)
    
    NOTA: il Dyntopo funziona SOLO in Sculpt Mode.
    Dopo, torna in Object Mode per sculpt procedurale Python.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='SCULPT')
    
    if not bpy.context.scene.tool_settings.sculpt.use_dyntopo:
        bpy.ops.sculpt.dynamic_topology_toggle()
    
    sc = bpy.context.scene.tool_settings.sculpt
    sc.detail_type_method = method
    if method == 'RELATIVE':
        sc.detail_size = detail_size
    else:
        sc.constant_detail_resolution = constant_detail
    
    bpy.ops.object.mode_set(mode='OBJECT')

def apply_sculpt_smooth_brush(obj, strength=1.0, size=50):
    """
    Applica uno smooth globale tramite Sculpt Mode operator.
    Meno preciso del smooth procedurale ma più rapido su mesh grandi.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='SCULPT')
    
    bpy.context.scene.tool_settings.sculpt.use_symmetry_x = False
    # Nota: bpy.ops.sculpt.brush_stroke non è facilmente invocabile da Python
    # Usa il smooth procedurale (global_smooth) invece
    
    bpy.ops.object.mode_set(mode='OBJECT')
```

---

## SCULPT → SHAPE KEY

Per animare tra una forma sculpted e la forma originale.

```python
def sculpt_to_shape_key(obj, key_name, sculpt_fn, basis_name="Basis"):
    """
    Esegue sculpt_fn e salva il risultato come Shape Key.
    L'oggetto torna alla forma originale dopo.
    
    sculpt_fn : callable(obj) — la funzione di sculpting da applicare
    
    Esempio:
        def add_smile(obj):
            brush(obj, (0.04, -0.08, 0.02), 0.03, 0.005, 'normal', 'smooth')
            brush(obj, (-0.04,-0.08, 0.02), 0.03, 0.005, 'normal', 'smooth')
        
        sculpt_to_shape_key(face, "Smile", add_smile)
        # Ora face ha due shape keys: Basis e Smile
    """
    # Salva posizioni originali
    original = [v.co.copy() for v in obj.data.vertices]
    
    # Assicurati che esista Basis key
    if not obj.data.shape_keys:
        obj.shape_key_add(name=basis_name, from_mix=False)
    
    # Applica sculting
    sculpt_fn(obj)
    
    # Salva come shape key
    sk = obj.shape_key_add(name=key_name, from_mix=False)
    for i, v in enumerate(obj.data.vertices):
        sk.data[i].co = v.co.copy()
    
    # Ripristina posizioni originali
    for i, v in enumerate(obj.data.vertices):
        v.co = original[i]
    obj.data.update()
    
    return sk
```

---

## PATTERN — Forme Organiche Comuni

### Mela / Pera / Agrumi
```python
def make_apple(name="Apple", radius=0.12):
    """Mela procedurale completa — testato e verificato visivamente."""
    # Base
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=64,
        ring_count=48, location=(0,0,0))
    obj = bpy.context.active_object; obj.name = name
    obj.data.shade_smooth()
    
    top_z = radius; bot_z = -radius
    
    # Dimple (fossetta) in cima
    brush(obj, (0, 0, top_z), radius*0.37, -radius*0.23, 'normal', 'sharp')
    
    # Appiattimento base
    brush(obj, (0, 0, bot_z), radius*0.46, -radius*0.15, 'z', 'sphere')
    
    # Bump equatoriale (4 lobi)
    for deg in [0, 90, 180, 270]:
        a = math.radians(deg)
        cx, cy = radius * math.cos(a), radius * math.sin(a)
        brush(obj, (cx, cy, 0), radius*0.58, radius*0.067, 'normal', 'smooth')
    
    # Schiacciamento verticale (mela più larga che alta)
    flatten_axis(obj, 'z', 0.88)
    
    # Safe place — base a z=0
    safe_place(obj)
    return obj

def make_pear(name="Pear", height=0.16):
    """Pera — base larga, parte alta stretta con dimple."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=height*0.5, segments=64,
        ring_count=48, location=(0,0,0))
    obj = bpy.context.active_object; obj.name = name
    obj.data.shade_smooth()
    
    h = height
    # Restringe la parte alta (pinch)
    pinch(obj, (0,0, h*0.3), radius=h*0.35, strength=0.5, axis='z')
    # Dimple top
    brush(obj, (0, 0, h*0.5), h*0.12, -h*0.12, 'normal', 'sharp')
    # Allarga parte bassa
    brush(obj, (0, 0,-h*0.15), h*0.4, h*0.04, 'normal', 'smooth')
    
    safe_place(obj)
    return obj
```

### Roccia / Asteroid
```python
def make_rock(name="Rock", size=0.15, seed=42):
    """Roccia irregolare con noise multi-ottava."""
    bpy.ops.mesh.primitive_ico_sphere_add(radius=size, subdivisions=4,
        location=(0,0,0))
    obj = bpy.context.active_object; obj.name = name
    
    # Remesh per topologia uniforme
    remesh_voxel(obj, voxel_size=size*0.06)
    
    # Noise multi-scala (forma grossa + dettaglio fine)
    displace_noise(obj, scale=3.0,  strength=size*0.15, seed=seed,   octaves=2)
    displace_noise(obj, scale=8.0,  strength=size*0.04, seed=seed+1, octaves=4)
    displace_noise(obj, scale=20.0, strength=size*0.01, seed=seed+2, octaves=3)
    
    # Smooth leggero per eliminare artefatti
    global_smooth(obj, strength=0.1, iterations=2)
    
    obj.data.shade_smooth()
    safe_place(obj)
    return obj
```

### Terreno procedurale
```python
def make_terrain(name="Terrain", size=2.0, resolution=80, height=0.3, seed=0):
    """
    Piano terreno con heightmap procedurale.
    resolution : n. vertici per lato (80→6400 vertici, 120→14400)
    height     : altezza massima del terreno [BU]
    """
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=resolution,
        y_subdivisions=resolution, size=size, location=(0,0,0))
    obj = bpy.context.active_object; obj.name = name
    
    mw = obj.matrix_world
    for v in obj.data.vertices:
        wp = mw @ v.co
        # Noise multi-ottava per terreno realistico
        h = (noise3d(wp.x*2, wp.y*2, 0, seed, octaves=6, persistence=0.55) + 1) * 0.5
        v.co.z = h * height
    
    obj.data.update()
    obj.data.shade_smooth()
    return obj
```

---

## SAFE PLACE — Posizionamento dopo sculpt

Dopo il sculpting la mesh può essere centrata male.
`safe_place` corregge automaticamente usando world bounds.

```python
def safe_place(obj, x=0.0, y=0.0, z=0.0, anchor='bottom'):
    """
    Posiziona l'oggetto nel world space dopo sculting.
    Usa sempre questa — mai obj.location = (x,y,z) direttamente.
    
    anchor: 'bottom' → il punto più basso dell'oggetto va a z
            'center' → il centro geometrico va a (x,y,z)
            'top'    → il punto più alto va a z
    
    NOTA: necessita view_layer.update() per matrix_world corretta.
    """
    bpy.context.view_layer.update()
    mw = obj.matrix_world
    wv = [mw @ v.co for v in obj.data.vertices]
    
    xs = [v.x for v in wv]; ys = [v.y for v in wv]; zs = [v.z for v in wv]
    cx = (min(xs)+max(xs))/2
    cy = (min(ys)+max(ys))/2
    cz = (min(zs)+max(zs))/2
    
    # Offset per correggere il centro geometrico
    ox = obj.location.x - cx
    oy = obj.location.y - cy
    oz = obj.location.z - cz
    
    if anchor == 'bottom':
        bfc = cz - min(zs)   # distanza dal centro al fondo
        obj.location = (x + ox, y + oy, z + oz + bfc)
    elif anchor == 'top':
        bfc = max(zs) - cz
        obj.location = (x + ox, y + oy, z + oz - bfc)
    else:  # center
        obj.location = (x + ox, y + oy, z + oz)
    
    bpy.context.view_layer.update()
```

---

## MATERIALE POST-SCULPT — SSS + noise per organici

```python
def mat_organic(name, base_color, sss_color=None, roughness=0.55,
                noise_scale=8.0, noise_strength=0.08, coat=0.0):
    """
    Materiale per oggetti organici sculpted: SSS + variazione noise + coat.
    
    base_color    : tuple RGB [0-1] — colore principale
    sss_color     : colore SSS (None = variante più rossa di base_color)
    noise_scale   : frequenza variazione colore superficiale
    noise_strength: intensità variazione colore [0-1]
    coat          : coat lucido [0-1] (0.5=mela, 0=pelle opaca)
    
    Esempi:
        mat_organic("Apple",  (0.72, 0.04, 0.02), coat=0.55)
        mat_organic("Skin",   (0.84, 0.61, 0.50), roughness=0.65)
        mat_organic("Orange", (0.95, 0.45, 0.05), noise_scale=12)
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    tree = m.node_tree; tree.nodes.clear()
    
    out  = tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    inp = [i.name for i in bsdf.inputs]
    
    # Noise texture → colore
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value    = noise_scale
    noise.inputs['Detail'].default_value   = 5.0
    noise.inputs['Roughness'].default_value = 0.6
    
    # Mix: colore base + variazione noise
    # Blender 5.x: usa ShaderNodeMix con data_type='RGBA' (NON ShaderNodeMixRGB!)
    mix = tree.nodes.new('ShaderNodeMix')
    mix.data_type  = 'RGBA'
    mix.blend_type = 'MIX'
    mix.inputs[6].default_value = (*base_color, 1.0)   # Color A = base
    # Color B = variante leggermente diversa
    c2 = tuple(min(1, c * (1 + noise_strength)) for c in base_color)
    mix.inputs[7].default_value = (*c2, 1.0)           # Color B = variante
    tree.links.new(noise.outputs['Fac'], mix.inputs[0])
    tree.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    
    bsdf.inputs['Roughness'].default_value = roughness
    
    # SSS
    sss_c = sss_color or tuple(min(1, c * 0.7) for c in base_color)
    for sn in ['Subsurface Weight', 'Subsurface']:
        if sn in inp:
            bsdf.inputs[sn].default_value = 0.15; break
    if 'Subsurface Radius' in inp:
        bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.2, 0.1)
    if 'Subsurface Scale' in inp:
        bsdf.inputs['Subsurface Scale'].default_value = 0.008
    
    # Coat (lucido superficiale per frutta, pelle tesa)
    if coat > 0:
        for cn in ['Coat Weight', 'Clearcoat']:
            if cn in inp:
                bsdf.inputs[cn].default_value = coat; break
        for cr in ['Coat Roughness', 'Clearcoat Roughness']:
            if cr in inp:
                bsdf.inputs[cr].default_value = 0.08; break
    
    return m
```

---

## REGOLE QUALITÀ SCULPTING

1. **Remesh prima dello sculpt** — mai sculpting su mesh con topologia irregolare.
   `remesh_voxel(obj, voxel_size)` dà topologia uniforme → brush uniformi.

2. **Ordine brush**: forma globale → forma media → dettaglio fine.
   Non iniziare con il dettaglio (rughe) prima di aver definito la forma (schiacciamento, dimple).

3. **`build_kd()` ad ogni iterazione** se la mesh è stata modificata.
   Il KDTree usa le posizioni al momento della costruzione — se i vertici si sono mossi
   le query spaziali tornano risultati errati.

4. **`safe_place()` dopo ogni sessione di sculpt** — mai leggere `obj.location`
   per determinare la posizione dei vertici. Usa sempre world bounds.

5. **`view_layer.update()`** prima di qualsiasi calcolo con `matrix_world`.

6. **Noise displacement DOPO smooth** — il pattern è:
   `forma base → smooth leggero → noise fine → smooth leggerissimo finale`.

7. **ShaderNodeMixRGB è deprecato** in Blender 5.x → usa `ShaderNodeMix`
   con `data_type='RGBA'`, Color A = `inputs[6]`, Color B = `inputs[7]`, output = `outputs[2]`.

8. **SSS richiede Cycles** per risultati fotorealistici. EEVEE Next supporta SSS
   ma meno preciso. Per preview usa EEVEE, per finale usa Cycles.

---

## ANALISI RICHIESTA

| Keyword | Tecnica |
|---------|---------|
| `mela / pera / frutto` | make_apple / make_pear + mat_organic |
| `roccia / asteroide / pietra` | make_rock + displace_noise multi-scala |
| `terreno / paesaggio` | make_terrain + noise3d heightmap |
| `ruga / piega / cuciture` | crease() + displace_wave |
| `dimple / fossetta / ombelico` | brush(..., 'sharp', negativo) |
| `pelle / organico / SSS` | displace_noise fine + mat_organic |
| `smooth / leviga / artefatti` | smooth_pass / global_smooth |
| `animabile / morphing` | sculpt_to_shape_key |
| `topologia uniforme` | remesh_voxel prima |

**Se richiesta ambigua → chiedi: "L'oggetto ha una forma base riconoscibile
(sfera, cilindro, cubo)? Ha dettagli di superficie (rughe, pori, bump)?
Deve essere animato?"**

## Output

- Codice Python completo, nessun placeholder
- Sempre: remesh → brush dalla forma grossa al dettaglio → smooth finale
- Usa mat_organic per oggetti biologici (SSS + noise + coat)
- Dopo esecuzione: get_screenshot → analisi visiva → itera brush
- safe_place() sempre alla fine prima del render
