---
description: >
  Skill per simulazioni fisiche in Blender: Rigid Body, Soft Body, Cloth (con Pressure),
  Force Fields e Particles. Gestisce setup modifier, presets per materiale/tipo,
  bake workflow e gotchas API Blender 5.x. Viene invocata dal coordinator quando
  l'oggetto deve cadere, rimbalzare, deformarsi, svolazzare o essere simulato.
  Include tabelle presets testate e funzioni Python pronte all'uso.
allowed-tools:
  - mcp__Blender__execute_blender_code
  - mcp__Blender__get_screenshot_of_window_as_image
  - mcp__Blender__render_viewport_to_path
  - Read
---

# Skill: Blender Physics & Simulation

Sei un esperto di simulazioni fisiche in Blender. Il tuo ruolo è aggiungere
dinamiche realistiche a oggetti già modellati — caduta, rimbalzo, deformazione,
svolazzamento — usando il modifier/sistema più appropriato e i parametri corretti
per Blender 5.x.

---

## ROUTING — Quale sistema usare?

| Scenario | Sistema | Note |
|----------|---------|------|
| Oggetto rigido che cade/rimbalza/crolla | **Rigid Body** | nessuna deformazione |
| Oggetto morbido che si schiaccia (gelatina, cuscino) | **Soft Body** | deformazione mesh |
| Pallone / oggetto gonfiabile | **Cloth + Pressure** | `use_pressure` presente in 5.x solo su Cloth |
| Tessuto, tenda, bandiera, vestito | **Cloth** | preset built-in: Cotton/Silk/Denim/Leather |
| Vento, attrazione, turbolenza su altri oggetti | **Force Field** | si combina con Cloth/Soft Body |
| Pioggia, polvere, capelli, erba | **Particles** | Emitter o Hair |
| Liquido che scorre / si versa | **Fluid (FLIP)** | setup separato, costoso |

> **Regola priorità:** Cloth batte Soft Body per oggetti gonfiabili (Blender 5.x ha rimosso
> `use_pressure` da Soft Body ma non da Cloth). Rigid Body batte tutto per oggetti non deformabili.

---

## CONNESSIONE — MCP

```python
mcp__Blender__execute_blender_code(code="""
import bpy
# ... codice simulazione ...
result = {"ok": True}
""")
```

---

## RIGID BODY

### Concetti base

```
ACTIVE  → oggetto che si muove guidato dalla fisica (palla, cubo che cade)
PASSIVE → oggetto fermo che fa da collider (pavimento, muro, tavolo)
```

### Setup standard

```python
import bpy

def setup_rigid_body_active(obj, preset="rubber_ball"):
    """
    Aggiunge Rigid Body ACTIVE all'oggetto.
    Deve essere attivo (bpy.context.view_layer.objects.active = obj).
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    rb = obj.rigid_body
    rb.type = 'ACTIVE'

    # Collision shape (scegli in base alla geometria):
    # 'SPHERE'       → sfere, oggetti rotondi — più veloce e preciso
    # 'BOX'          → cubi, oggetti rettangolari
    # 'CAPSULE'      → cilindri, oggetti allungati
    # 'CONVEX_HULL'  → oggetti convessi qualsiasi — buon compromesso
    # 'MESH'         → mesh arbitraria — preciso ma lento, evitare per oggetti veloci
    rb.collision_shape = 'SPHERE'  # per palle

    _apply_rb_preset(rb, preset)
    return rb

def setup_rigid_body_passive(obj, friction=0.5, restitution=0.3):
    """Aggiunge Rigid Body PASSIVE (collider statico)."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    rb = obj.rigid_body
    rb.type              = 'PASSIVE'
    rb.collision_shape   = 'MESH'    # per piani e superfici complesse
    rb.friction          = friction
    rb.restitution       = restitution
    rb.use_margin        = True
    rb.collision_margin  = 0.001
    return rb

def _apply_rb_preset(rb, preset):
    """Applica parametri preset al rigid body."""
    PRESETS = {
        # preset: (mass, friction, restitution, linear_damp, angular_damp)
        "rubber_ball":  (0.50, 0.80, 0.85, 0.04, 0.10),
        "soccer_ball":  (0.45, 0.60, 0.70, 0.04, 0.10),
        "tennis_ball":  (0.06, 0.65, 0.75, 0.04, 0.10),
        "bowling_ball": (6.80, 0.35, 0.10, 0.04, 0.08),
        "metal":        (5.00, 0.50, 0.30, 0.04, 0.10),
        "wood":         (2.00, 0.60, 0.20, 0.05, 0.15),
        "glass":        (3.00, 0.40, 0.10, 0.04, 0.10),
        "ice":          (5.00, 0.02, 0.15, 0.04, 0.05),
        "stone":        (10.0, 0.80, 0.05, 0.04, 0.20),
        "plastic_hard": (0.30, 0.55, 0.40, 0.04, 0.10),
        "foam":         (0.10, 0.70, 0.05, 0.10, 0.30),
    }
    if preset not in PRESETS:
        raise ValueError(f"Preset sconosciuto: {preset}. Disponibili: {list(PRESETS)}")
    mass, friction, rest, lin_damp, ang_damp = PRESETS[preset]
    rb.mass             = mass
    rb.friction         = friction
    rb.restitution      = rest     # 0=nessun rimbalzo, 1=rimbalzo perfetto
    rb.linear_damping   = lin_damp
    rb.angular_damping  = ang_damp
    rb.use_margin       = True
    rb.collision_margin = 0.001
```

### Setup scena Rigid Body

```python
def setup_rb_scene(frame_start=1, frame_end=150, substeps=10, solver=20):
    """
    Configura la scena per la simulazione Rigid Body.

    substeps_per_frame: più alto = più preciso (default 10)
      10  → uso normale
      20  → oggetti veloci (palla che rimbalza ad alta velocità)
      50  → collisioni molto rapide / oggetti piccoli

    solver_iterations: stabilità vincoli (default 10, aumentare per pile di oggetti)
    """
    sc = bpy.context.scene
    sc.frame_start = frame_start
    sc.frame_end   = frame_end
    sc.gravity     = (0.0, 0.0, -9.81)

    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()

    rb_world = sc.rigidbody_world
    rb_world.substeps_per_frame = substeps
    rb_world.solver_iterations  = solver
    rb_world.point_cache.frame_start = frame_start
    rb_world.point_cache.frame_end   = frame_end
    return rb_world
```

### Bake Rigid Body → keyframes

```python
def bake_rigid_body(frame_start=1, frame_end=150, step=1):
    """
    Converte la simulazione Rigid Body in keyframe sull'oggetto.
    Dopo il bake, la simulazione non serve più — i keyframe sono indipendenti.

    IMPORTANTE: eseguire DOPO aver settato tutta la scena.
    """
    bpy.ops.rigidbody.bake_to_keyframes(
        frame_start=frame_start,
        frame_end=frame_end,
        step=step
    )
```

### Esempio completo — palla che rimbalza (Rigid Body)

```python
import bpy
from mathutils import Vector

# Scena
sc = bpy.context.scene
sc.gravity = (0, 0, -9.81)

# Ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0, 0, 2.0))
ball = bpy.context.active_object
ball.name = "Ball"

# Ground
bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Physics
setup_rb_scene(frame_start=1, frame_end=100, substeps=20)
setup_rigid_body_active(ball, preset="soccer_ball")
setup_rigid_body_passive(ground, friction=0.5, restitution=0.3)

# Simula step-by-step (per visualizzare senza bake)
sc.frame_set(1)
for f in range(2, 101):
    sc.frame_set(f)
    bpy.context.view_layer.update()

# Oppure bake in keyframe:
# bake_rigid_body(1, 100)
```

---

## SOFT BODY

### Gotcha critico — API Blender 5.x

> ⚠️ In Blender 4.x → 5.x diversi attributi sono stati rinominati.
> `use_pressure` e `pressure_factor` sono stati **rimossi** da Soft Body.
> Per oggetti gonfiabili (palloni) usare **Cloth con Pressure**.

Attributi corretti Blender 5.x su `obj.soft_body`:

| Blender 3.x | Blender 5.x | Descrizione |
|-------------|-------------|-------------|
| `sb.damp` | `sb.damping` | Smorzamento molle edge |
| `sb.use_pressure` | ❌ rimosso | Pressione interna |
| `sb.pressure_factor` | ❌ rimosso | Fattore pressione |
| `coll.friction` | `coll.friction_factor` | CollisionSettings |
| `coll.dampening` | `coll.damping` | Damping collisione |

### Presets Soft Body

```python
import bpy

def setup_soft_body(obj, preset="rubber"):
    """
    Aggiunge Soft Body all'oggetto con preset.

    Presets disponibili:
      "jelly"      → gelatina, flan — molto morbido, rimane deformato
      "rubber"     → gomma rigida — rimbalza, recupera la forma
      "foam"       → spugna — si deforma facilmente, recupero lento
      "flesh"      → carne / muscolo — morbido con recupero medio
      "cloth_like" → telo — si piega ma non comprime
    """
    bpy.context.view_layer.objects.active = obj
    obj.modifiers.new("Softbody", type='SOFT_BODY')
    sb = obj.soft_body

    PRESETS = {
        # preset: (use_goal, goal_def, pull, push, damping, shear, bend, stiff_quads, friction, mass)
        "jelly":      (False, 0.0, 0.30, 0.30, 12.0, 0.2, 0.1, False, 0.5, 1.5),
        "rubber":     (False, 0.0, 0.95, 0.95,  3.0, 0.4, 0.8, True,  0.5, 0.8),
        "foam":       (False, 0.0, 0.50, 0.20, 20.0, 0.3, 0.3, True,  0.8, 0.3),
        "flesh":      (False, 0.0, 0.60, 0.40,  8.0, 0.2, 0.2, False, 0.6, 1.2),
        "cloth_like": (False, 0.0, 0.55, 0.10,  5.0, 0.5, 0.3, False, 0.3, 0.4),
    }
    if preset not in PRESETS:
        raise ValueError(f"Preset: {list(PRESETS.keys())}")

    use_goal, goal_def, pull, push, damping, shear, bend, stiff_q, friction, mass = PRESETS[preset]

    sb.use_goal        = use_goal
    sb.goal_default    = goal_def
    sb.use_edges       = True
    sb.pull            = pull
    sb.push            = push
    sb.damping         = damping   # ← CORRETTO: non sb.damp
    sb.shear           = shear
    sb.bend            = bend
    sb.use_stiff_quads = stiff_q
    sb.friction        = friction
    sb.mass            = mass
    sb.speed           = 1.0
    sb.step_min        = 10
    sb.step_max        = 300
    sb.error_threshold = 0.05
    sb.use_edge_collision = True
    return sb

def setup_collision_passive(obj):
    """
    Aggiunge Collision modifier a un oggetto passivo (piano, muro).
    Funziona con Soft Body E Cloth.
    """
    obj.modifiers.new("Collision", type='COLLISION')
    coll = obj.collision
    coll.thickness_outer  = 0.002
    coll.thickness_inner  = 0.001
    coll.damping          = 0.1      # ← CORRETTO: non dampening
    # coll.friction_factor = 0.3    # ← se disponibile in versione corrente
    return coll
```

---

## CLOTH + PRESSURE

### Perché Cloth per oggetti gonfiabili

Cloth è l'unico sistema in Blender 5.x ad avere ancora `use_pressure`.
Parametri chiave per un pallone:

```
tension_stiffness   → resistenza allo stiramento (alta = rigido)
compression_stiffness → resistenza alla compressione
bending_stiffness   → resistenza alla flessione
use_pressure        → abilita pressione interna
uniform_pressure_force → intensità pressione (positivo = gonfia, negativo = aspira)
```

### Presets Cloth (equivalenti ai built-in di Blender)

```python
import bpy

def setup_cloth(obj, preset="cotton", pressure=None, pressure_factor=1.0):
    """
    Aggiunge Cloth modifier con preset.

    preset: "cotton" | "silk" | "denim" | "leather" | "rubber" | "inflated_ball"
    pressure: None (disabilitato) | float (forza pressione uniforme)
              > 0 → gonfia, < 0 → aspira
              Valori tipici: 3-5 (palloncino), 8-15 (pallone da calcio)
    pressure_factor: fattore volume per la pressione (default 1.0)
    """
    mod = obj.modifiers.new("Cloth", type='CLOTH')
    cs  = mod.settings   # ClothSettings

    PRESETS = {
        # (quality, mass, tension, compression, shear, bending, ten_damp, comp_damp, bend_damp, air_damp)
        "cotton":       (5,  0.30, 15.0, 15.0, 0.5,  0.5,  0.0, 0.0, 0.5, 1.0),
        "silk":         (5,  0.15,  5.0,  5.0, 0.5,  0.05, 0.0, 0.0, 0.5, 1.0),
        "denim":        (5,  1.50, 40.0, 40.0, 1.0, 10.0,  0.0, 0.0, 0.5, 1.0),
        "leather":      (5,  1.00, 80.0, 80.0, 2.0, 20.0,  0.0, 0.0, 0.5, 1.0),
        "rubber":       (5,  1.50, 15.0, 15.0, 5.0,  5.0,  0.0, 0.0, 0.5, 1.0),
        "viscose":      (5,  0.20, 10.0, 10.0, 0.5,  0.2,  0.0, 0.0, 0.5, 1.0),
        # Speciale: oggetti gonfiabili — da usare con pressure > 0
        "inflated_ball": (8, 0.30, 40.0, 40.0, 3.0,  1.0,  0.1, 0.1, 0.1, 0.5),
        "balloon":       (6, 0.10, 20.0, 20.0, 1.0,  0.1,  0.0, 0.0, 0.1, 0.3),
    }
    if preset not in PRESETS:
        raise ValueError(f"Preset: {list(PRESETS.keys())}")

    q, mass, tens, comp, shear, bend, td, cd, bd, air = PRESETS[preset]

    cs.quality                   = q
    cs.mass                      = mass
    cs.tension_stiffness         = tens
    cs.compression_stiffness     = comp
    cs.shear_stiffness           = shear
    cs.bending_stiffness         = bend
    cs.tension_damping           = td
    cs.compression_damping       = cd
    cs.bending_damping           = bd
    cs.air_damping               = air

    # Pressure (oggetti gonfiabili)
    if pressure is not None:
        cs.use_pressure              = True
        cs.uniform_pressure_force    = pressure        # forza pressione
        cs.pressure_factor           = pressure_factor # fattore volume (1.0 default)
        cs.fluid_density             = 0.0             # densità fluido interno (0 = aria)

    # Collision detection del cloth con se stesso
    coll_s = mod.collision_settings
    coll_s.distance_min  = 0.005
    coll_s.impulse_clamp = 0.0

    return mod, cs


# ── ESEMPIO COMPLETO — Pallone da calcio (Cloth + Pressure) ────────────────
"""
import bpy
from mathutils import Vector

sc = bpy.context.scene
sc.frame_start = 1
sc.frame_end   = 80
sc.render.fps  = 24
sc.gravity     = (0, 0, -9.81)

# Ball — UV sphere con abbastanza vertices per deformazione smooth
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, segments=32, ring_count=24,
                                      location=(0, 0, 1.5))
ball = bpy.context.active_object
ball.name = "Ball"
ball.data.shade_smooth()

# Ground — con Collision modifier
bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
setup_collision_passive(ground)

# Cloth + Pressure sul pallone
setup_cloth(ball, preset="inflated_ball", pressure=8.0)

# Simula
sc.frame_set(1)
for f in range(2, 81):
    sc.frame_set(f)
    bpy.context.view_layer.update()
"""
```

### Parametri Pressure — Guida rapida

```python
# uniform_pressure_force = pressione interna

# Oggetto molle / poco gonfiato (palloncino):
cs.uniform_pressure_force = 2.0
cs.tension_stiffness = 5.0    # poco rigido

# Pallone da calcio / basket:
cs.uniform_pressure_force = 8.0
cs.tension_stiffness = 40.0   # rigido

# Pallone molto rigido (medica ball):
cs.uniform_pressure_force = 20.0
cs.tension_stiffness = 80.0

# Aspirazione (oggetto che si sgonfia verso l'interno):
cs.uniform_pressure_force = -3.0

# Cuscinetto d'aria / air mattress:
cs.uniform_pressure_force = 5.0
cs.mass = 0.8
cs.bending_stiffness = 0.5    # si piega facilmente ma mantiene volume
```

---

## FORCE FIELDS

Force Fields si aggiungono come oggetti separati e influenzano Soft Body, Cloth e Particles.

```python
import bpy
from mathutils import Vector

def add_force_field(ff_type, location=(0,0,0), strength=1.0, **kwargs):
    """
    Crea un Force Field object.

    ff_type: 'WIND' | 'VORTEX' | 'TURBULENCE' | 'FORCE' | 'DRAG' | 'HARMONIC'
    strength: intensità del campo
    kwargs: attributi extra su obj.field

    WIND    → vento direzionale (dipende dalla rotazione dell'oggetto)
    VORTEX  → campo vorticoso centrifugo
    TURBULENCE → rumore vorticoso, simula vento irregolare
    FORCE   → attrazione/repulsione radiale sferica
    DRAG    → rallenta oggetti vicini (smorzamento)
    HARMONIC → attrazione verso il centro (molla)
    """
    bpy.ops.object.effector_add(type=ff_type, location=location)
    ff_obj = bpy.context.active_object
    ff_obj.name = f"FF_{ff_type}"

    field = ff_obj.field
    field.strength = strength

    for key, val in kwargs.items():
        if hasattr(field, key):
            setattr(field, key, val)

    return ff_obj

# ── Preset Force Fields ────────────────────────────────────────────

def wind_preset(strength=3.0, noise=0.4, location=(0,0,1), direction=(1,0,0)):
    """
    Vento con turbolenza. Agisce su Cloth, Soft Body, Particles.

    IMPORTANTE: la direzione del vento dipende dall'asse -Z dell'oggetto.
    Ruotare l'oggetto per cambiare direzione, oppure:
    """
    from mathutils import Vector
    ff = add_force_field('WIND', location=location, strength=strength)
    ff.field.noise     = noise      # turbolenza (0=liscio, 1=molto turbolento)
    ff.field.seed      = 42
    ff.field.flow      = 0.5       # inerzia del vento (0=istantaneo, 1=lento)
    # Punta nella direzione desiderata
    d = Vector(direction).normalized()
    ff.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ff

def vortex_preset(strength=5.0, location=(0,0,0)):
    """Campo vorticoso — fa girare Cloth e Particles attorno all'asse Z."""
    return add_force_field('VORTEX', location=location, strength=strength,
                           flow=0.3, noise=0.1)

def turbulence_preset(strength=2.0, size=0.5, location=(0,0,0)):
    """Turbolenza casuale — simula aria mossa, ottimo su bandiere e capelli."""
    return add_force_field('TURBULENCE', location=location, strength=strength,
                           size=size, noise=0.5, seed=7)
```

---

## BAKE WORKFLOW

### Pattern standard — step-by-frame (semplice, sempre funziona)

```python
def simulate_frames(frame_start=1, frame_end=100, verbose=True):
    """
    Calcola la simulazione stepping frame per frame.
    Funziona per Soft Body, Cloth e Rigid Body.

    NOTA: il risultato viene tenuto in RAM (cache non persistente).
    Alla riapertura del file la sim va ricalcolata.
    Per cache persistente → usare bake_to_disk().
    """
    sc = bpy.context.scene
    sc.frame_set(frame_start)
    for f in range(frame_start + 1, frame_end + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        if verbose and f % 10 == 0:
            print(f"  Frame {f}/{frame_end}")
    print(f"Simulazione completata: {frame_end - frame_start} frame")
```

### Trovare il frame di impatto/massima deformazione

```python
def find_min_z_frame(obj, frame_start=1, frame_end=100):
    """
    Cerca il frame con il vertice più basso (massimo squash/impatto).
    Utile per trovare il frame migliore per il render still.

    Richiede che la simulazione sia già stata calcolata.
    """
    sc = bpy.context.scene
    min_z = float('inf')
    best_frame = frame_start

    for f in range(frame_start, frame_end + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval  = obj.evaluated_get(depsgraph)
        z = min((obj_eval.matrix_world @ v.co).z for v in obj_eval.data.vertices)
        if z < min_z:
            min_z = z
            best_frame = f

    return best_frame, min_z

# Uso:
# impact_frame, min_z = find_min_z_frame(ball, 1, 50)
# sc.frame_set(impact_frame)
# → render il frame di massimo squash
```

### Bake su disco (cache persistente)

```python
def bake_to_disk(obj, modifier_name, frame_start=1, frame_end=100):
    """
    Bake su disco. Dopo il bake, la sim non va ricalcolata alla riapertura.
    Funziona per Soft Body e Cloth.
    """
    mod = obj.modifiers.get(modifier_name)
    if mod is None:
        raise ValueError(f"Modifier '{modifier_name}' non trovato su {obj.name}")

    cache = mod.point_cache
    cache.frame_start = frame_start
    cache.frame_end   = frame_end
    cache.use_disk_cache = True

    bpy.context.view_layer.objects.active = obj
    bpy.ops.ptcache.bake_all(bake=True)
```

---

## SCENA TIPO — Setup completo

```python
import bpy, math
from mathutils import Vector

def setup_physics_scene(frame_end=100, fps=24, gravity=-9.81):
    """Setup base scena per simulazione fisica."""
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end   = frame_end
    sc.render.fps  = fps
    sc.gravity     = (0.0, 0.0, gravity)

    # Rigid Body world (se si usa Rigid Body)
    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    sc.rigidbody_world.substeps_per_frame = 10
    sc.rigidbody_world.solver_iterations  = 20
    sc.rigidbody_world.point_cache.frame_end = frame_end

    return sc
```

---

## GOTCHAS & API CHANGES — Blender 5.x

### Tabella completa cambi API

| Cosa | Vecchio (≤ 3.6) | Corretto (5.x) | Impatto |
|------|-----------------|----------------|---------|
| Edge spring damping SoftBody | `sb.damp` | `sb.damping` | AttributeError |
| Pressione interna SoftBody | `sb.use_pressure` | ❌ rimosso | usare Cloth |
| Fattore pressione SoftBody | `sb.pressure_factor` | ❌ rimosso | usare Cloth |
| Attrito CollisionSettings | `coll.friction` | `coll.friction_factor` | AttributeError |
| Damping CollisionSettings | `coll.dampening` | `coll.damping` | AttributeError |
| Bake single cache | `bpy.ops.ptcache.bake()` | context override richiesto | OperatorError |

### Collisioni — parametri CollisionSettings corretti

```python
# CollisionSettings (Blender 5.x) — attributi verificati:
coll.thickness_outer  = 0.002   # spessore esterno di collisione
coll.thickness_inner  = 0.001   # spessore interno
coll.damping          = 0.1     # damping all'impatto (0=massimo rimbalzo)
coll.cloth_friction   = 0.3     # attrito per Cloth
# coll.friction_factor → esiste in alcune versioni, non in tutte
# Verifica con: [a for a in dir(obj.collision) if 'fric' in a.lower()]
```

### Soft Body — attributi verificati Blender 5.x

```python
# Tutti gli attributi SoftBodySettings verificati:
sb.use_goal        # bool — goal weights
sb.goal_default    # float 0-1 — goal strength
sb.goal_spring     # float — goal spring stiffness
sb.goal_friction   # float — goal friction
sb.use_edges       # bool — edge springs
sb.pull            # float — spring pull
sb.push            # float — spring push
sb.damping         # float — spring damping  ← NON damp
sb.shear           # float — shear stiffness
sb.bend            # float — bend stiffness
sb.use_stiff_quads # bool — quad reinforcement
sb.friction        # float — air friction
sb.mass            # float — vertex mass
sb.speed           # float — sim speed
sb.step_min        # int — solver min steps
sb.step_max        # int — solver max steps
sb.error_threshold # float — solver tolerance
sb.use_edge_collision  # bool — edge-based collision
sb.use_face_collision  # bool — face-based collision (costoso)
sb.ball_stiff      # float — collision ball stiffness
sb.ball_size       # float — collision ball size
```

### Cloth — attributi verificati Blender 5.x

```python
# ClothSettings via mod.settings:
cs.quality                  # int — steps per frame
cs.mass                     # float
cs.tension_stiffness        # float
cs.compression_stiffness    # float
cs.shear_stiffness          # float
cs.bending_stiffness        # float
cs.tension_damping          # float
cs.compression_damping      # float
cs.bending_damping          # float
cs.air_damping              # float
cs.use_pressure             # bool ← ANCORA PRESENTE in 5.x ✓
cs.uniform_pressure_force   # float ← pressione uniforme ✓
cs.pressure_factor          # float ← fattore volume ✓
cs.fluid_density            # float ← densità fluido interno

# CollisionSettings del Cloth via mod.collision_settings:
coll_s.distance_min         # float — distanza minima self-collision
coll_s.impulse_clamp        # float — clamp dell'impulso di collisione
coll_s.friction             # float — attrito
```

### Rigid Body — attributi verificati

```python
# Su obj.rigid_body (dopo bpy.ops.rigidbody.object_add()):
rb.type                # 'ACTIVE' | 'PASSIVE'
rb.mass                # float
rb.friction            # float 0-1
rb.restitution         # float 0-1 (bounciness)
rb.linear_damping      # float 0-1
rb.angular_damping     # float 0-1
rb.collision_shape     # 'SPHERE'|'BOX'|'CAPSULE'|'CYLINDER'|'CONE'|'CONVEX_HULL'|'MESH'
rb.use_margin          # bool
rb.collision_margin    # float
rb.kinematic           # bool — kinematic object (animated, no physics)
rb.enabled             # bool
```

---

## WORKFLOW TIPICI

### Workflow 1 — Rigid Body (oggetto che rimbalza senza deformarsi)

```
1. setup_physics_scene()
2. setup_rigid_body_active(ball, preset="soccer_ball")
3. setup_rigid_body_passive(floor)
4. simulate_frames(1, 100)
5. find_min_z_frame(ball) → frame impatto
6. render
```

### Workflow 2 — Cloth + Pressure (pallone gonfiabile)

```
1. setup_physics_scene()
2. setup_collision_passive(floor)
3. setup_cloth(ball, preset="inflated_ball", pressure=8.0)
4. simulate_frames(1, 80)
5. find_min_z_frame(ball) → frame squash
6. render
```

### Workflow 3 — Cloth (tessuto/bandiera)

```
1. Crea piano con abbastanza suddivisioni (subdivide 10-20x)
2. Vertex group "pin" per i vertici fissi (es. bordo superiore)
3. setup_cloth(cloth_obj, preset="cotton")
4. cloth.settings.vertex_group_mass = "pin"  # vincola i vertici pinned
5. Aggiungi Force Field vento se necessario
6. simulate_frames(1, 100)
7. render
```

---

## COORDINATOR ROUTING — Aggiunta alla tabella

Da aggiungere alla tabella ROUTING SKILL in blender-coordinator:

```
| Oggetto che cade/rimbalza senza deformarsi | blender-physics (Rigid Body) |
| Oggetto morbido che si schiaccia/deforma   | blender-physics (Soft Body)  |
| Pallone / oggetto gonfiabile               | blender-physics (Cloth+Pressure) |
| Tessuto / vestito / bandiera / tenda       | blender-physics (Cloth)      |
| Vento / turbolenza / forza su oggetto sim  | blender-physics (Force Field)|
| Pioggia / polvere / particelle             | blender-physics (Particles)  |
```

Priorità nel coordinator:
- `blender-physics` batte `blender-arch` se l'oggetto deve muoversi/deformarsi fisicamente
- `blender-physics` va DOPO `blender-arch`/`blender-procedural` (prima si modella, poi si simula)
- Per oggetti gonfiabili: **sempre Cloth+Pressure**, mai Soft Body in Blender 5.x
