---
description: >
  Skill di rigging procedurale per Blender. Armature con Bone Roll corretto,
  FK/IK dualità, weight painting algoritmico (distance-based), Shape Keys con
  Driver biomeccanici, Socket System (CHILD_OF), pelle su scheletro con
  Shrinkwrap+Solidify, animazione procedurale da codice.
  Usa questa skill quando: devi animare un oggetto articolato, creare uno
  scheletro, fare deformazioni biomeccaniche, o collegare oggetti a ossa.
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

# Skill: Blender Procedural Rigging

Sei un esperto di rigging anatomico e procedurale in Blender.
Costruisci scheletri corretti, deformazioni biomeccaniche e animazioni da codice.

---

## Connessione — MCP (predefinito)

```python
mcp__Blender__execute_blender_code(code="""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion
# ... codice ...
result = {"ok": True}
""")

mcp__Blender__get_screenshot_of_window_as_image()
mcp__Blender__render_viewport_to_path(output_path="C:/Users/josia/Downloads/rig_preview.png")
```

---

## IL PRINCIPIO FONDAMENTALE — Bone Roll e Frame Locali

Ogni osso in Blender ha un **frame locale** (assi X, Y, Z):
- **Y locale**: direzione testa→coda (sempre, non modificabile)
- **X locale**: determinato dal **Bone Roll**
- **Z locale**: B = Y × X

**Bone Roll = 0** significa che l'asse X locale è allineato al mondo.
Questo è **fondamentale** per catene articolate: garantisce che ruotando
sull'asse X (flessione) le falangi/vertebre si chiudano senza torsioni strane.

```
Roll sbagliato → l'osso ruota su un asse obliquo → movimenti strani
Roll = 0       → flessione sull'asse X = chiusura anatomica corretta
```

**Come verificare:**
```python
# In Edit Mode — controlla il roll di ogni osso
for bone in arm.data.edit_bones:
    print(f"{bone.name}: roll = {math.degrees(bone.roll):.2f}°")
# Se non è 0° (o 90° per assi specifici), correggilo
```

---

## ARMATURE — Creazione e Convenzioni

```python
import bpy, math
from mathutils import Vector

def create_armature(name="Rig"):
    """
    Crea un'armatura vuota pronta per ricevere ossa.
    Ritorna (arm_obj, armature).
    """
    bpy.ops.object.armature_add(enter_editmode=True,
                                 align='WORLD', location=(0,0,0))
    arm_obj  = bpy.context.active_object
    arm_obj.name = name
    armature = arm_obj.data
    armature.name = name + "_Armature"
    # Rimuovi l'osso di default
    armature.edit_bones.remove(armature.edit_bones[0])
    return arm_obj, armature

def add_bone(armature, name, head, tail, parent=None,
             connected=False, roll=0.0, layer=0):
    """
    Aggiunge un osso all'armatura (deve essere in Edit Mode).
    
    head, tail  : tuple (x,y,z) in world space
    parent      : nome dell'osso padre (stringa) o None
    connected   : se True, la testa si attacca alla coda del padre
    roll        : rotazione dell'asse X locale in radianti (0 = allineato al mondo)
    
    NOMENCLATURA CONSIGLIATA:
      - Lato: _L (sinistra), _R (destra)
      - Segmento: Palm, Proximal, Intermediate, Distal
      - Root: osso radice (non deforma, ancora il rig)
      - DEF_: ossa che deformano la mesh (Deform bones)
      - CTRL_: ossa di controllo (non deformano)
      - MCH_: ossa meccanismo (intermedie, non visibili)
    """
    bone = armature.edit_bones.new(name)
    bone.head  = Vector(head)
    bone.tail  = Vector(tail)
    bone.roll  = roll
    bone.use_deform = True
    if parent:
        bone.parent = armature.edit_bones[parent]
        bone.use_connect = connected
    return bone

# ── Esempio: dito indice ──────────────────────────────────────────────
def create_finger(armature, name, base_y, segments=None):
    """
    Crea una catena di ossa per un dito.
    
    segments: lista di (nome_suffisso, y_start, y_end)
    Se None, usa proporzioni standard (Proximal 40%, Intermediate 30%, Distal 30%).
    """
    if segments is None:
        segments = [
            ("Palm",         0.0,  -2.0),
            ("Proximal",    -2.0,  -4.0),
            ("Intermediate",-4.0,  -5.5),
            ("Distal",      -5.5,  -6.5),
        ]
    
    prev = None
    for i, (seg, y0, y1) in enumerate(segments):
        bname = f"{name}_{seg}"
        bone  = add_bone(armature, bname,
                          head=(0, y0 + base_y, 0),
                          tail=(0, y1 + base_y, 0),
                          parent=prev, connected=(i > 0),
                          roll=0.0)  # ← ROLL = 0: asse X orizzontale
        prev = bname
```

---

## FK / IK — DUALITÀ

**FK (Forward Kinematics)**: ruota ogni osso manualmente dalla radice alla punta.
Preciso, prevedibile, ma lento per animazioni complesse.

**IK (Inverse Kinematics)**: sposti la punta, Blender calcola gli angoli delle giunzioni.
Rapido per posare, ma meno preciso. Richiede un Pole Target per evitare flipping del ginocchio/gomito.

```python
def setup_ik(arm_obj, tip_bone_name, chain_count=3,
              pole_target=None, pole_bone=None, pole_angle=0):
    """
    Aggiunge un vincolo IK all'osso 'tip_bone_name'.
    Deve essere chiamato in POSE mode.
    
    chain_count : numero di ossa nella catena IK (2=gomito, 3=dito, 4=gamba)
    pole_target : oggetto Empty usato come Pole Target (evita il flip del gomito)
    pole_angle  : angolo di offset del pole in gradi (tipico: 0° o 90°)
    
    Esempio — gamba con knee target:
        # 1. Crea Empty per il knee
        bpy.ops.object.empty_add(location=(0, -2, 0.5))
        knee = bpy.context.active_object
        knee.name = "Knee_Target"
        # 2. Attiva pose mode sull'armatura
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        # 3. Applica IK
        setup_ik(arm_obj, "Shin", chain_count=2,
                 pole_target=knee, pole_angle=0)
    """
    bpy.context.view_layer.objects.active = arm_obj
    
    if bpy.context.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    
    pbone = arm_obj.pose.bones[tip_bone_name]
    ik    = pbone.constraints.new('IK')
    ik.chain_count = chain_count
    
    if pole_target:
        ik.pole_target      = pole_target
        ik.pole_subtarget   = pole_bone or ""
        ik.pole_angle       = math.radians(pole_angle)
    
    return ik

def setup_ik_target(arm_obj, tip_bone_name, target_obj=None, chain_count=3):
    """
    Alternativa: usa un Empty come target IK (la punta segue l'Empty).
    Crea automaticamente l'Empty se target_obj è None.
    """
    if target_obj is None:
        tip_world = arm_obj.pose.bones[tip_bone_name].tail
        bpy.ops.object.empty_add(location=arm_obj.matrix_world @ tip_world)
        target_obj = bpy.context.active_object
        target_obj.name = f"IK_{tip_bone_name}_Target"
    
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pbone = arm_obj.pose.bones[tip_bone_name]
    ik    = pbone.constraints.new('IK')
    ik.target      = target_obj
    ik.chain_count = chain_count
    return ik, target_obj

def toggle_ik_fk(arm_obj, bone_names, use_ik=True):
    """
    Commuta tra IK e FK per un gruppo di ossa.
    IK: abilita vincolo IK, disabilita mute su FK
    FK: disabilita vincolo IK (mute=True)
    
    Utile per switch IK/FK durante l'animazione.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for bn in bone_names:
        for c in arm_obj.pose.bones[bn].constraints:
            if c.type == 'IK':
                c.mute = not use_ik
```

---

## WEIGHT PAINTING ALGORITMICO

Il weight painting procedurale assegna pesi ai vertex group in base
alla distanza da punti di controllo. Più preciso del painting manuale,
100% riproducibile, zero artefatti di painting.

### Smoothstep interpolator
```python
def smoothstep(x):
    """Interpolazione cubica [0,1] → [0,1]. Derivata zero agli estremi."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def smootherstep(x):
    """Quintica — transizione ancora più morbida. Per blend tra giunzioni."""
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)
```

### Weight painting per coordinata (catene lineari)
```python
def weight_paint_by_coord(mesh_obj, bone_ranges, coord_axis='Y',
                           blend_zone=0.3):
    """
    Assegna pesi ai vertex group in base alla coordinata di ogni vertice.
    Ideale per catene lineari (dito, colonna, arto).
    
    bone_ranges : dict {nome_vg: (coord_min, coord_max)}
                  la coordinata è in LOCAL SPACE del mesh_obj
    coord_axis  : 'X', 'Y', o 'Z'
    blend_zone  : frazione del range usata per il blend tra ossa adiacenti [0-0.5]
    
    Esempio (dito lungo Y, da 0 a -6.5):
        weight_paint_by_coord(skin, {
            "Palm":         ( 0.0, -2.0),
            "Proximal":    (-2.0, -4.0),
            "Intermediate":(-4.0, -5.5),
            "Distal":      (-5.5, -6.5),
        }, coord_axis='Y', blend_zone=0.3)
    """
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[coord_axis]
    
    # Crea vertex group se non esistono
    vgs = {}
    for name in bone_ranges:
        vg = mesh_obj.vertex_groups.get(name)
        if vg is None:
            vg = mesh_obj.vertex_groups.new(name=name)
        vg.add(list(range(len(mesh_obj.data.vertices))), 0.0, 'REPLACE')
        vgs[name] = vg
    
    names   = list(bone_ranges.keys())
    ranges  = list(bone_ranges.values())
    
    for v in mesh_obj.data.vertices:
        coord = v.co[axis_idx]
        for i, (name, (cmin, cmax)) in enumerate(zip(names, ranges)):
            span  = cmax - cmin if cmax != cmin else 1e-6
            blend = abs(span) * blend_zone
            
            if min(cmin, cmax) <= coord <= max(cmin, cmax):
                # Dentro il range: peso 1 al centro, blend agli estremi
                t = (coord - cmin) / span
                
                w = 1.0
                # Blend con l'osso precedente (inizio range)
                if i > 0 and abs(blend) > 1e-8:
                    fade_in  = abs((coord - cmin) / blend)
                    if fade_in < 1.0:
                        w = min(w, smoothstep(fade_in))
                        # Osso precedente prende il complemento
                        vgs[names[i-1]].add([v.index],
                            (1.0 - smoothstep(fade_in)), 'ADD')
                # Blend con l'osso successivo (fine range)
                if i < len(names)-1 and abs(blend) > 1e-8:
                    fade_out = abs((cmax - coord) / blend)
                    if fade_out < 1.0:
                        w = min(w, smoothstep(fade_out))
                        vgs[names[i+1]].add([v.index],
                            (1.0 - smoothstep(fade_out)), 'ADD')
                
                if w > 0:
                    vgs[name].add([v.index], w, 'ADD')

### Weight painting per distanza da punto 3D
def weight_paint_by_distance(mesh_obj, vg_name, center_local,
                               max_dist, falloff='SMOOTH'):
    """
    Assegna pesi in base alla distanza da un punto 3D in spazio locale.
    Ideale per aree di influenza circolari (nocca, spalla, muscolatura).
    
    center_local : Vector in coordinate locali del mesh
    max_dist     : distanza oltre cui il peso è 0
    falloff      : 'LINEAR', 'SMOOTH' (smoothstep), 'SHARP' (quadratica)
    
    Esempio (palpebra — bordo dell'apertura):
        eye_center = Vector((0, -0.5, 0.35))
        weight_paint_by_distance(eyelid, "UpperLid", eye_center,
                                  max_dist=0.9, falloff='SMOOTH')
    """
    vg = mesh_obj.vertex_groups.get(vg_name)
    if vg is None:
        vg = mesh_obj.vertex_groups.new(name=vg_name)
    
    center = Vector(center_local)
    for v in mesh_obj.data.vertices:
        dist = (v.co - center).length
        t    = max(0.0, 1.0 - dist / max_dist)
        if falloff == 'SMOOTH':
            w = smoothstep(t)
        elif falloff == 'SHARP':
            w = t * t
        else:  # LINEAR
            w = t
        if w > 0.001:
            vg.add([v.index], w, 'REPLACE')
```

---

## SHAPE KEYS + DRIVER — Biomeccanica Procedurale

I Shape Key + Driver creano deformazioni reattive: la nocca si solleva
quando il dito si piega, l'occhio si gonfia quando si chiude, il muscolo
si contrae quando l'osso ruota.

```python
def add_shape_key_with_driver(mesh_obj, key_name, driver_bone,
                               arm_obj, transform='ROT_X',
                               expression="abs(rot) / 1.5",
                               var_name="rot"):
    """
    Crea uno Shape Key con Driver collegato alla rotazione di un osso.
    
    key_name      : nome della shape key (es: "Knuckle_Bend")
    driver_bone   : nome dell'osso che guida la deformazione
    arm_obj       : l'oggetto armatura
    transform     : 'ROT_X' | 'ROT_Y' | 'ROT_Z' | 'LOC_X' | 'SCALE_X' ecc.
    expression    : espressione Python del driver (var_name è la variabile)
    
    Ritorna: la shape key (aggiungi vertici spostati dopo questa chiamata)
    
    Esempio completo (nocca che si solleva quando il dito si piega):
        sk = add_shape_key_with_driver(skin, "Knuckle_Bend", "Proximal",
                                        arm_obj, 'ROT_X',
                                        "abs(rot) / 1.5")
        # Poi sposta i vertici della nocca nella sk.data:
        for i, v in enumerate(skin.data.vertices):
            if is_near_knuckle(v.co):
                influence = knuckle_weight(v.co)
                sk.data[i].co.z += 0.3 * influence
    """
    # Assicurati che esista la Basis key
    if not mesh_obj.data.shape_keys:
        mesh_obj.shape_key_add(name="Basis", from_mix=False)
    
    sk = mesh_obj.shape_key_add(name=key_name, from_mix=False)
    sk.value = 0.0
    
    # Aggiunge il Driver
    fc     = sk.driver_add("value")
    driver = fc.driver
    driver.type = 'SCRIPTED'
    
    var            = driver.variables.new()
    var.name       = var_name
    var.type       = 'TRANSFORMS'
    t              = var.targets[0]
    t.id           = arm_obj
    t.bone_target  = driver_bone
    t.transform_type  = transform
    t.transform_space = 'LOCAL_SPACE'
    
    driver.expression = expression
    return sk

def deform_knuckle(mesh_obj, joint_y, influence_radius=0.8,
                   lift_z=0.3, compress_z=0.4):
    """
    Applica la deformazione della nocca a una shape key già creata.
    Chiama questa DOPO add_shape_key_with_driver.
    
    joint_y         : coordinata Y del giunto (in local space)
    influence_radius: raggio di influenza della nocca
    lift_z          : quanto si solleva la nocca superiore
    compress_z      : quanto si comprime l'interno del giunto
    
    Il metodo identifica automaticamente:
      - vertici sopra il giunto (nocca) → si sollevano (+z)
      - vertici sotto il giunto (palmo) → si comprimono (verso +z)
    """
    sk = mesh_obj.data.shape_keys.key_blocks[-1]  # l'ultima shape key
    
    for i, v in enumerate(mesh_obj.data.vertices):
        dist = abs(v.co.y - joint_y)
        if dist < influence_radius:
            influence = smoothstep(1.0 - dist / influence_radius)
            if v.co.z > 0:   # parte superiore → nocca
                sk.data[i].co.z += lift_z * influence
                sk.data[i].co.y += 0.2 * influence
            else:             # parte inferiore → compressione
                sk.data[i].co.z += compress_z * influence
```

---

## SOCKET SYSTEM — Collegare Oggetti a Ossa

Il Socket System usa il vincolo `CHILD_OF` per ancorare oggetti a ossa.
Permette di attaccare armi, attrezzi, oggetti a una mano/braccio.

```python
def socket_attach(mesh_obj, arm_obj, bone_name,
                  local_offset=(0,0,0), local_rotation=(0,0,0)):
    """
    Attacca mesh_obj all'osso bone_name tramite vincolo CHILD_OF.
    
    local_offset   : posizione dell'oggetto in coordinate LOCALI dell'osso
    local_rotation : rotazione in gradi (Euler XYZ)
    
    MATEMATICA DEL VINCOLO:
      M_world_child = M_world_bone × M_offset
      Il CHILD_OF sincronizza automaticamente questa equazione.
    
    Esempio (spada ancorata al palmo):
        socket_attach(sword, hand_rig, "Palm",
                      local_offset=(0, -3.5, -0.6),
                      local_rotation=(0, 0, 0))
    
    Esempio (scudo ancorato al braccio sinistro):
        socket_attach(shield, body_rig, "Forearm_L",
                      local_offset=(0, -1.0, 0.1),
                      local_rotation=(0, 90, 0))
    """
    c = mesh_obj.constraints.new('CHILD_OF')
    c.target     = arm_obj
    c.subtarget  = bone_name
    
    # Offset locale rispetto all'osso
    mesh_obj.location = Vector(local_offset)
    mesh_obj.rotation_euler = tuple(math.radians(r) for r in local_rotation)
    
    # Calcola l'inverse matrix per il vincolo
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.constraint.childof_set_inverse(
        constraint=c.name, owner='OBJECT')
    
    return c

def socket_detach(mesh_obj, bone_name=None):
    """Rimuove tutti i vincoli CHILD_OF (o solo quello verso bone_name)."""
    for c in list(mesh_obj.constraints):
        if c.type == 'CHILD_OF':
            if bone_name is None or c.subtarget == bone_name:
                mesh_obj.constraints.remove(c)
```

---

## PELLE BIOMECCANICA — Shrinkwrap + Solidify

Tecnica per creare pelle che avvolge uno scheletro curvo:
1. Crea una mesh di partenza dalla forma generale (sfera, cilindro)
2. Ritaglia le aperture (occhio a mandorla, bocca, ecc.) in Edit Mode
3. Shrinkwrap: la mesh si "avvolge" sull'oggetto sottostante
4. Solidify: aggiunge spessore
5. Armature: deformazione da scheletro

```python
def skin_with_shrinkwrap(skin_obj, target_obj, wrap_method='NEAREST_SURFACEPOINT',
                          offset=0.005, thickness=0.04, subsurf_levels=2):
    """
    Configura i modificatori per pelle biomeccanica.
    L'ordine è critico: Armature → Shrinkwrap → Solidify → SubSurf.
    
    wrap_method:
      'NEAREST_SURFACEPOINT' : proietta sul punto più vicino — stabile su mesh curve
      'PROJECT'              : proietta lungo una direzione — per superfici piatte
      'NEAREST_VERTEX'       : snapping ai vertici — meno smooth
    
    Esempio (palpebra su sfera occhio):
        create_eyeball()  → eyeball
        create_eyelid()   → eyelid_mesh (con apertura a mandorla)
        skin_with_shrinkwrap(eyelid_mesh, eyeball,
                              offset=0.005, thickness=0.04)
    """
    # 1. Shrinkwrap
    sw = skin_obj.modifiers.new("Shrinkwrap", "SHRINKWRAP")
    sw.target      = target_obj
    sw.wrap_method = wrap_method
    sw.offset      = offset
    
    # 2. Solidify (spessore verso l'esterno)
    sol = skin_obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness  = thickness
    sol.offset     = 1.0
    
    # 3. SubSurf (leviga il risultato)
    sub = skin_obj.modifiers.new("Subdivision", "SUBSURF")
    sub.levels        = subsurf_levels
    sub.render_levels = subsurf_levels + 1
    
    skin_obj.data.shade_smooth()
    return sw, sol, sub

def bind_armature(mesh_obj, arm_obj):
    """
    Collega mesh_obj all'armatura arm_obj come modifier.
    Da chiamare DOPO aver configurato i vertex group con weight_paint_*.
    Il modifier Armature deve essere il PRIMO nella stack.
    """
    # Aggiungi Armature come primo modificatore
    arm_mod = mesh_obj.modifiers.new("Armature", "ARMATURE")
    arm_mod.object = arm_obj
    
    # Sposta in cima alla stack (prima di Shrinkwrap e Solidify)
    while mesh_obj.modifiers[0].name != arm_mod.name:
        bpy.ops.object.modifier_move_up(modifier=arm_mod.name)
    
    # Parent senza vincolo di offset
    mesh_obj.parent = arm_obj
    mesh_obj.parent_type = 'OBJECT'
    mesh_obj.matrix_parent_inverse.identity()
    return arm_mod
```

---

## ANIMAZIONE PROCEDURALE — Keyframe da Codice

```python
def animate_bone(arm_obj, bone_name, frames_rots,
                  rotation_mode='XYZ'):
    """
    Anima un osso con keyframe da codice.
    
    frames_rots : lista di (frame, (rx_deg, ry_deg, rz_deg))
    
    Esempio (dito che si chiude e si riapre):
        animate_bone(hand_rig, "Proximal", [
            (1,  (0,   0, 0)),   # aperto
            (30, (70,  0, 0)),   # chiuso
            (60, (0,   0, 0)),   # riaperto
        ])
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    pbone = arm_obj.pose.bones[bone_name]
    pbone.rotation_mode = rotation_mode
    
    for frame, rot_deg in frames_rots:
        bpy.context.scene.frame_set(frame)
        pbone.rotation_euler = tuple(math.radians(r) for r in rot_deg)
        pbone.keyframe_insert(data_path="rotation_euler", frame=frame)
    
    bpy.ops.object.mode_set(mode='OBJECT')

def animate_grasp(arm_obj, open_frame=1, close_frame=30, open_frame2=60,
                   finger_bones=None):
    """
    Animazione procedurale di presa (open → close → open).
    
    finger_bones : dict {bone_name: (open_rot, closed_rot)}
                   angoli in gradi sull'asse X
    
    Default: catena indice standard (Proximal, Intermediate, Distal).
    """
    if finger_bones is None:
        finger_bones = {
            "Proximal":     (0, 70),
            "Intermediate": (0, 90),
            "Distal":       (0, 60),
        }
    
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    for bname, (open_rot, close_rot) in finger_bones.items():
        pbone = arm_obj.pose.bones[bname]
        pbone.rotation_mode = 'XYZ'
        
        for frame, deg in [(open_frame,  open_rot),
                            (close_frame, close_rot),
                            (open_frame2, open_rot)]:
            bpy.context.scene.frame_set(frame)
            pbone.rotation_euler = (math.radians(deg), 0, 0)
            pbone.keyframe_insert(data_path="rotation_euler", frame=frame)
    
    bpy.ops.object.mode_set(mode='OBJECT')

def set_interpolation(arm_obj, interp='BEZIER'):
    """
    Imposta il tipo di interpolazione per tutte le f-curves dell'armatura.
    'BEZIER'  : morbido (default — buono per movimenti organici)
    'LINEAR'  : lineare (buono per turntable, meccanico)
    'CONSTANT': scatto (per animazioni stop-motion o flag)
    """
    if arm_obj.animation_data and arm_obj.animation_data.action:
        for fc in arm_obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = interp
```

---

## WORKFLOW COMPLETO — Mano con Presa

```python
# ══ STEP 1: Armatura ══════════════════════════════════════════
arm_obj, arm = create_armature("Hand_Rig")

# Ossa in edit mode (già attivo da create_armature)
joints = [("Palm", (0,-2.0,0)), ("Proximal",(0,-4.0,0)),
          ("Intermediate",(0,-5.5,0)), ("Distal",(0,-6.5,0))]
prev = None
for i, (name, tail) in enumerate(joints):
    head = (0, ([0,-2.0,-4.0,-5.5][i]), 0)
    add_bone(arm, name, head, tail, parent=prev,
             connected=(i>0), roll=0.0)
    prev = name

bpy.ops.object.mode_set(mode='OBJECT')

# ══ STEP 2: Mesh cilindrica ══════════════════════════════════
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.6,
    depth=7.0, location=(0,-3.25,0), rotation=(math.radians(90),0,0))
skin = bpy.context.active_object
skin.name = "Finger_Skin"
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=20)
bpy.ops.object.mode_set(mode='OBJECT')

# ══ STEP 3: Weight Painting ═══════════════════════════════════
weight_paint_by_coord(skin, {
    "Palm":         ( 0.0,  -2.0),
    "Proximal":     (-2.0,  -4.0),
    "Intermediate": (-4.0,  -5.5),
    "Distal":       (-5.5,  -6.5),
}, coord_axis='Y', blend_zone=0.25)

# ══ STEP 4: Shape Key Nocca ═══════════════════════════════════
sk = add_shape_key_with_driver(skin, "Knuckle_Bend", "Proximal",
                                arm_obj, 'ROT_X', "abs(rot)/1.5")
deform_knuckle(skin, joint_y=-2.0)

# ══ STEP 5: Bind armatura ════════════════════════════════════
bind_armature(skin, arm_obj)

# ══ STEP 6: Socket (oggetto nella mano) ══════════════════════
bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=4.0,
    location=(0,0,0), rotation=(0,math.radians(90),0))
handle = bpy.context.active_object
handle.name = "Handle"
socket_attach(handle, arm_obj, "Palm",
              local_offset=(0,-3.5,-0.6))

# ══ STEP 7: Animazione presa ══════════════════════════════════
animate_grasp(arm_obj, open_frame=1, close_frame=30, open_frame2=60)
bpy.context.scene.frame_end = 80
```

---

## WORKFLOW COMPLETO — Palpebra Biomeccanica

```python
# 1. Sfera oculare
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32,
    radius=1.0, location=(0,0,0))
eyeball = bpy.context.active_object
eyeball.name = "Eyeball"
eyeball.data.shade_smooth()

# 2. Maschera facciale (sfera leggermente più grande con apertura a mandorla)
bpy.ops.mesh.primitive_uv_sphere_add(segments=100, ring_count=50,
    radius=1.02, location=(0,0,0))
eyelid = bpy.context.active_object
eyelid.name = "Eyelid"

# Ritaglia l'apertura in Edit Mode (parabola a mandorla)
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(eyelid.data)
width, height = 0.8, 0.35
to_del = [v for v in bm.verts if v.co.y > 0.1 or
           (v.co.y < 0.2 and abs(v.co.x) < width and
            abs(v.co.z) <= height * (1-(v.co.x/width)**2))]
bmesh.ops.delete(bm, geom=to_del, context='VERTS')
bmesh.update_edit_mesh(eyelid.data)
bpy.ops.object.mode_set(mode='OBJECT')

# 3. Weight paint per upper/lower lid
weight_paint_by_distance(eyelid, "EyelidControl_Upper",
    Vector((0,-0.5, 0.35)), max_dist=0.9, falloff='SMOOTH')
weight_paint_by_distance(eyelid, "EyelidControl_Lower",
    Vector((0,-0.5,-0.35)), max_dist=0.9, falloff='SMOOTH')

# 4. Shrinkwrap + Solidify
skin_with_shrinkwrap(eyelid, eyeball, offset=0.005, thickness=0.04)
```

---

## REGOLE QUALITÀ RIGGING

1. **Bone Roll = 0** su tutti gli assi di flessione primari (dita, gomito, ginocchio).
   Eccezione: assi di abduzione/adduzione possono avere roll 90°.

2. **Ordine modificatori** è critico:
   `Armature → Shrinkwrap → Solidify → SubSurf`
   Invertire Armature e Shrinkwrap causa deformazioni errate.

3. **Normalizza i vertex group** dopo il weight painting:
   Ogni vertice deve avere pesi che sommano a 1.0.
   `bpy.ops.object.vertex_group_normalize_all()` in Edit Mode.

4. **Driver expression** deve essere limitata a [0,1]:
   Usa `min(1, max(0, abs(rot)/1.5))` per sicurezza.

5. **Pole Target** obbligatorio su catene IK con 2+ ossa.
   Senza pole target il gomito/ginocchio flippa a 180°.

6. **`bpy.ops.constraint.childof_set_inverse`** da chiamare dopo
   ogni socket_attach — imposta la matrice inversa corretta.

7. **Test in Pose Mode** prima del render:
   Muovi l'osso radice → verifica che tutto il rig si muova insieme.
   Ruota l'osso foglia → verifica che i driver si attivino.

---

## ANALISI RICHIESTA

| Keyword | Tecnica |
|---------|---------|
| `mano / dito / falange` | create_finger + weight_paint_by_coord + animate_grasp |
| `occhio / palpebra` | sfera UV + maschera a mandorla + skin_with_shrinkwrap |
| `gamba / ginocchio / gomito` | IK con pole target (setup_ik) |
| `braccio / catena` | create_armature + add_bone + setup_ik_target |
| `colonna / vertebra` | catena lineare + parallel_transport (usa blender-procedural) |
| `spada / scudo / attrezzo` | socket_attach + CHILD_OF |
| `nocca / muscolo / gonfiore` | Shape Key + Driver (add_shape_key_with_driver) |
| `presa / animazione pugno` | animate_grasp |
| `FK / IK switch` | toggle_ik_fk |
| `pelle / skin / deformazione` | bind_armature + weight_paint_* |

**Se richiesta ambigua → chiedi: "L'oggetto deve deformarsi (pelle su scheletro)
o solo seguire un osso rigidamente (socket)?"**

## Output

- Codice Python completo, nessun placeholder
- Bone Roll = 0 su tutti gli assi primari
- Weight paint sempre con smoothstep (non lineare)
- Dopo esecuzione: screenshot → analisi visiva → itera
- Driver expression sempre limitata a [0,1]
