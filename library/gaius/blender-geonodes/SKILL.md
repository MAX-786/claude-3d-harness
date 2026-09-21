---
description: >
  Skill di Geometry Nodes procedurale per Blender. Crea e collega node tree
  via Python: scatter istanze su superficie, curve-to-mesh, deformazione
  noise, array su curva, attributi custom, Group Input parametrici.
  Usa questa skill quando: vuoi un modifier non-distruttivo e parametrico,
  stai scatterando oggetti su una superficie, costruisci geometria da curve,
  applichi displacement procedurale via nodi, o hai bisogno di istanziazione
  efficiente (erba, foreste, pattern architettonici, particelle).
allowed-tools:
  - Bash
  - Read
  - Write
  - mcp__Blender__execute_blender_code
  - mcp__Blender__get_screenshot_of_window_as_image
  - mcp__Blender__render_viewport_to_path
  - mcp__Blender__get_objects_summary
---

# Skill: Blender Geometry Nodes (Procedurale)

Sei un esperto di Geometry Nodes in Blender via Python.
Costruisci node tree parametrici e non-distruttivi da codice.

---

## Connessione — MCP (predefinito)

```python
mcp__Blender__execute_blender_code(code="""
import bpy
# ... codice ...
result = {"ok": True}
""")

mcp__Blender__get_screenshot_of_window_as_image()
mcp__Blender__render_viewport_to_path(output_path="C:/Users/josia/Downloads/gn.png")
```

---

## IL PRINCIPIO — GeoNodes vs Python bmesh

| | bmesh (blender-arch/procedural) | Geometry Nodes |
|-|----------------------------------|----------------|
| Distruttivo | Sì — modifica la mesh | No — modifier on top |
| Parametrico | No (dopo apply) | Sì — sliders sempre |
| Istanziazione | Slow (N oggetti separati) | Fast (GPU instancing) |
| Animabile | Solo con driver | Sì — natively |
| Complessità API | Media | Alta (node graph) |

**Usa GeoNodes quando:**
- Il risultato deve rimanere modificabile (number of instances, density...)
- Stai istanziando molti oggetti (> 50)
- Vuoi animare i parametri
- La forma deriva da una curva o da una superficie esistente

---

## SETUP BASE — Modifier + Node Group

```python
import bpy

def create_gn_modifier(obj, name="GeoNodes"):
    """
    Crea un modifier Geometry Nodes su obj e un node group vuoto.
    Ritorna (modifier, node_group, nodes, links).
    
    Blender 4.x/5.x: usa ng.interface.new_socket() per I/O,
    NON ng.inputs.new() / ng.outputs.new() (deprecati in 4.0).
    """
    mod = obj.modifiers.new(name, 'NODES')
    ng  = bpy.data.node_groups.new(name + "_Tree", 'GeometryNodeTree')
    mod.node_group = ng
    
    # Interfaccia I/O — ORDINE IMPORTANTE: OUTPUT prima di INPUT
    if hasattr(ng, 'interface'):
        ng.interface.new_socket("Geometry", in_out="OUTPUT",
                                socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="INPUT",
                                socket_type="NodeSocketGeometry")
    
    # Nodi Group Input e Output (terminali del grafo)
    in_node  = ng.nodes.new("NodeGroupInput")
    out_node = ng.nodes.new("NodeGroupOutput")
    in_node.location  = (-400, 0)
    out_node.location = ( 400, 0)
    
    # Pass-through di default (geometry → output invariata)
    ng.links.new(in_node.outputs[0], out_node.inputs[0])
    
    return mod, ng, ng.nodes, ng.links

# Uso base:
# bpy.ops.mesh.primitive_plane_add(size=2)
# plane = bpy.context.active_object
# mod, ng, nodes, links = create_gn_modifier(plane, "MyGeoNodes")
```

---

## HELPER FUNCTIONS

```python
def add_node(nodes, bl_idname, location=(0,0), **props):
    """
    Aggiunge un nodo e imposta proprietà.
    props: coppie nome=valore per inputs o attributi del nodo.
    
    Esempi:
        add_node(nodes, 'GeometryNodeMeshPrimitiveSphere',
                 location=(200, 0),
                 inputs={'Radius': 0.05})
        
        add_node(nodes, 'FunctionNodeRandomValue',
                 location=(0, -200),
                 data_type='FLOAT_VECTOR')
    """
    n = nodes.new(bl_idname)
    n.location = location
    
    for k, v in props.items():
        if k == 'inputs':
            for input_name, val in v.items():
                if input_name in n.inputs:
                    n.inputs[input_name].default_value = val
        else:
            setattr(n, k, v)
    
    return n

def link(links, from_node, from_socket, to_node, to_socket):
    """
    Collega due nodi. Accetta indici interi o nomi stringa per i socket.
    
    Esempi:
        link(links, dist, "Points", inst, "Points")
        link(links, math, 0, out_node, 0)   # per indice
    """
    if isinstance(from_socket, int):
        fs = from_node.outputs[from_socket]
    else:
        fs = from_node.outputs[from_socket]
    
    if isinstance(to_socket, int):
        ts = to_node.inputs[to_socket]
    else:
        ts = to_node.inputs[to_socket]
    
    return links.new(fs, ts)

def add_group_input(ng, name, socket_type, default=None, min_val=None, max_val=None):
    """
    Aggiunge un Group Input parametrico (slider visibile nel modifier).
    
    socket_type: 'NodeSocketFloat' | 'NodeSocketInt' | 'NodeSocketVector'
                 'NodeSocketBool' | 'NodeSocketObject' | 'NodeSocketMaterial'
                 'NodeSocketGeometry' | 'NodeSocketColor'
    
    Esempio:
        add_group_input(ng, "Density",   "NodeSocketFloat", default=500, min_val=0, max_val=5000)
        add_group_input(ng, "Scale",     "NodeSocketFloat", default=1.0, min_val=0.01, max_val=5.0)
        add_group_input(ng, "Instance",  "NodeSocketObject")
        add_group_input(ng, "Seed",      "NodeSocketInt",   default=0)
    
    Dopo averlo aggiunto, accedilo via in_node.outputs[name] nel grafo.
    Il valore è modificabile via modifier nel Properties panel.
    """
    sock = ng.interface.new_socket(name, in_out="INPUT", socket_type=socket_type)
    if default is not None:
        try: sock.default_value = default
        except: pass
    if min_val is not None:
        try: sock.min_value = min_val
        except: pass
    if max_val is not None:
        try: sock.max_value = max_val
        except: pass
    return sock
```

---

## PATTERN 1 — Scatter istanze su superficie

Il pattern più comune: distribuisce copie di un oggetto su una mesh.
Usato per: sprinkles su donut, erba su terreno, pietre su pavimento,
foglie su rami, chiodi su tavola, bottoni su tessuto.

```python
def scatter_on_surface(host_obj, instance_obj, density=500.0,
                        random_rotation=True, align_to_normal=True,
                        scale_min=0.8, scale_max=1.2, seed=0,
                        name="Scatter"):
    """
    Scatter di instance_obj sulla superficie di host_obj.
    
    density        : istanze per m² [BU²]
    random_rotation: ruota casualmente ogni istanza sull'asse normale
    align_to_normal: orienta le istanze lungo la normale della superficie
    scale_min/max  : range scala casuale (1.0 = nessuna variazione)
    seed           : seed casuale — cambia per layout diverso
    
    Pipeline: Geometry → Distribute Points on Faces →
              Instance on Points → Rotate → Scale → Realize → Output
    
    Esempi:
        # Sprinkles su donut
        scatter_on_surface(icing, sprinkle, density=3000, seed=42)
        
        # Erba su terreno
        scatter_on_surface(terrain, grass_blade, density=200,
                           scale_min=0.7, scale_max=1.5, seed=7)
        
        # Pietre su pavimento
        scatter_on_surface(floor, rock, density=50,
                           random_rotation=True, align_to_normal=False)
    """
    mod, ng, nds, lks = create_gn_modifier(host_obj, name)
    
    # Rimuovi il link pass-through di default
    for l in list(lks): lks.remove(l)
    
    in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
    out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")
    
    # Group Input parametrici
    add_group_input(ng, "Density", "NodeSocketFloat",
                    default=density, min_val=0, max_val=10000)
    add_group_input(ng, "Seed", "NodeSocketInt", default=seed)
    
    # Distribute Points on Faces
    dist = add_node(nds, "GeometryNodeDistributePointsOnFaces",
                    location=(0, 0), inputs={"Density": density})
    dist.distribute_method = "RANDOM"
    
    # Object Info (geometria dell'istanza)
    obj_info = add_node(nds, "GeometryNodeObjectInfo", location=(0, -200))
    obj_info.inputs["Object"].default_value = instance_obj
    obj_info.transform_space = 'ORIGINAL'
    
    # Instance on Points
    inst = add_node(nds, "GeometryNodeInstanceOnPoints", location=(300, 0))
    
    cur_x = 500
    last_out = ("Instances", inst)
    
    if align_to_normal:
        lks.new(dist.outputs["Normal"], inst.inputs["Rotation"])
    
    # Rotazione casuale
    if random_rotation:
        rand_rot = add_node(nds, "FunctionNodeRandomValue",
                            location=(0, -400))
        rand_rot.data_type = "FLOAT_VECTOR"
        rand_rot.inputs["Min"].default_value = (0, 0, 0)
        rand_rot.inputs["Max"].default_value = (6.2832, 6.2832, 6.2832)
        
        rot = add_node(nds, "GeometryNodeRotateInstances",
                       location=(cur_x, 0))
        lks.new(last_out[1].outputs[last_out[0]], rot.inputs["Instances"])
        lks.new(rand_rot.outputs[0], rot.inputs["Rotation"])
        last_out = ("Instances", rot)
        cur_x += 200
    
    # Scala casuale
    if scale_min != 1.0 or scale_max != 1.0:
        rand_sc = add_node(nds, "FunctionNodeRandomValue",
                           location=(cur_x - 200, -300))
        rand_sc.data_type = "FLOAT"
        rand_sc.inputs[2].default_value = scale_min   # Min float
        rand_sc.inputs[3].default_value = scale_max   # Max float
        
        sc_inst = add_node(nds, "GeometryNodeScaleInstances",
                           location=(cur_x, 0))
        lks.new(last_out[1].outputs[last_out[0]], sc_inst.inputs["Instances"])
        lks.new(rand_sc.outputs[1], sc_inst.inputs["Scale"])
        last_out = ("Instances", sc_inst)
        cur_x += 200
    
    # Realize Instances (converte in mesh reale)
    realize = add_node(nds, "GeometryNodeRealizeInstances",
                       location=(cur_x, 0))
    
    # Join Geometry (mantiene la superficie host + le istanze)
    join = add_node(nds, "GeometryNodeJoinGeometry",
                    location=(cur_x + 200, 0))
    
    # Collega tutto
    lks.new(in_nd.outputs[0],              dist.inputs["Mesh"])
    lks.new(in_nd.outputs["Density"],      dist.inputs["Density"])
    lks.new(dist.outputs["Points"],        inst.inputs["Points"])
    lks.new(obj_info.outputs["Geometry"],  inst.inputs["Instance"])
    lks.new(last_out[1].outputs[last_out[0]], realize.inputs["Geometry"])
    lks.new(in_nd.outputs[0],             join.inputs["Geometry"])
    lks.new(realize.outputs["Geometry"],  join.inputs["Geometry"])
    lks.new(join.outputs["Geometry"],     out_nd.inputs[0])
    
    return mod, ng
```

---

## PATTERN 2 — Curve to Mesh (tubo da curva)

Crea tubi, cavi, cornici, tubi idraulici da curve Bezier/NURBS.
Parametrico: cambia il profilo o la curva e il tubo si aggiorna.

```python
def curve_to_pipe(curve_obj, profile_radius=0.02, resolution=12,
                  name="CurvePipe"):
    """
    Genera un tubo circolare lungo una curva con Geometry Nodes.
    
    curve_obj      : oggetto curva Bezier/NURBS/Poly
    profile_radius : raggio del tubo [BU]
    resolution     : divisioni angolari della sezione circolare
    
    Pipeline: Curve Input → Curve to Mesh (con Circle profile) → Output
    
    Più flessibile di blender-arch pipe_along_points perché:
    - Il profilo può essere qualsiasi curva (ovale, quadrato...)
    - Tutto è non-distruttivo e animabile
    - La risoluzione è regolabile dopo creazione
    
    Esempi:
        # Tubo idraulico
        curve_to_pipe(pipe_curve, profile_radius=0.015)
        
        # Cavo elettrico (più sottile)
        curve_to_pipe(cable_curve, profile_radius=0.004, resolution=8)
        
        # Cornice architettonica (profilo rettangolare → usa curve_to_profile)
        curve_to_pipe(cornice_curve, profile_radius=0.05)
    """
    mod, ng, nds, lks = create_gn_modifier(curve_obj, name)
    for l in list(lks): lks.remove(l)
    
    in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
    out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")
    
    # Group Input per raggio (parametrico)
    add_group_input(ng, "Radius", "NodeSocketFloat",
                    default=profile_radius, min_val=0.001, max_val=1.0)
    
    # Curve Circle (profilo circolare)
    circle = add_node(nds, "GeometryNodeCurvePrimitiveCircle",
                      location=(0, -200),
                      inputs={"Resolution": resolution,
                              "Radius": profile_radius})
    circle.mode = 'RADIUS'
    
    # Curve to Mesh
    c2m = add_node(nds, "GeometryNodeCurveToMesh", location=(300, 0))
    c2m.inputs["Fill Caps"].default_value = True
    
    # Set Shade Smooth
    smooth = add_node(nds, "GeometryNodeSetShadeSmooth", location=(500, 0))
    smooth.inputs["Shade Smooth"].default_value = True
    
    lks.new(in_nd.outputs[0],         c2m.inputs["Curve"])
    lks.new(in_nd.outputs["Radius"],  circle.inputs["Radius"])
    lks.new(circle.outputs["Curve"],  c2m.inputs["Profile Curve"])
    lks.new(c2m.outputs["Mesh"],      smooth.inputs["Geometry"])
    lks.new(smooth.outputs["Geometry"], out_nd.inputs[0])
    
    return mod, ng


def curve_to_profile(curve_obj, profile_curve_obj, name="CurveProfile"):
    """
    Estrue un profilo personalizzato lungo una curva.
    profile_curve_obj: curva 2D che definisce la sezione (cornice, binario...)
    
    Esempio:
        # Crea profilo L (angolare)
        bpy.ops.curve.primitive_bezier_curve_add()
        profile = bpy.context.active_object
        # ... modifica i punti del profilo in Edit Mode ...
        
        curve_to_profile(rail_curve, profile)
    """
    mod, ng, nds, lks = create_gn_modifier(curve_obj, name)
    for l in list(lks): lks.remove(l)
    
    in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
    out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")
    
    # Object Info per il profilo
    prof_info = add_node(nds, "GeometryNodeObjectInfo", location=(0, -200))
    prof_info.inputs["Object"].default_value = profile_curve_obj
    
    # Object to Curve
    obj2curve = add_node(nds, "GeometryNodeObjectInfo", location=(0, -200))
    
    c2m = add_node(nds, "GeometryNodeCurveToMesh", location=(300, 0))
    c2m.inputs["Fill Caps"].default_value = True
    
    lks.new(in_nd.outputs[0],           c2m.inputs["Curve"])
    lks.new(prof_info.outputs["Geometry"], c2m.inputs["Profile Curve"])
    lks.new(c2m.outputs["Mesh"],        out_nd.inputs[0])
    
    return mod, ng
```

---

## PATTERN 3 — Deformazione noise (Set Position)

Deforma una mesh in modo procedurale e non-distruttivo.
Alternativa a blender-sculpt quando vuoi parametri animabili.

```python
def noise_deform(obj, scale=5.0, strength=0.05, detail=6.0,
                 direction='normal', seed=0, name="NoiseDeform"):
    """
    Deformazione noise non-distruttiva via Geometry Nodes.
    
    scale     : frequenza del noise (2=grosso, 8=medio, 20=fine)
    strength  : intensità dello spostamento [BU]
    detail    : ottave del noise (2=liscio, 8=rugoso)
    direction : 'normal' (lungo normali) | 'z' | 'xyz' (tutte le direzioni)
    
    A differenza di blender-sculpt, questo è completamente reversibile:
    basta disabilitare/rimuovere il modifier.
    
    Usi: terreno ondulato, superficie d'acqua, bandiera che sventola,
         superfici organiche parametriche, deformazione per animazione.
    """
    mod, ng, nds, lks = create_gn_modifier(obj, name)
    for l in list(lks): lks.remove(l)
    
    in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
    out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")
    
    # Group Inputs parametrici
    add_group_input(ng, "Strength", "NodeSocketFloat",
                    default=strength, min_val=0, max_val=1.0)
    add_group_input(ng, "Scale",    "NodeSocketFloat",
                    default=scale,   min_val=0.1, max_val=50.0)
    
    # Position (coordinate vertici)
    pos = add_node(nds, "GeometryNodeInputPosition", location=(-400, -200))
    
    # Normal (per direction='normal')
    if direction == 'normal':
        normal = add_node(nds, "GeometryNodeInputNormal", location=(-400, -400))
    
    # Noise Texture
    noise = add_node(nds, "ShaderNodeTexNoise", location=(-200, 0))
    noise.noise_dimensions = '3D'
    noise.inputs["Scale"].default_value  = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.5
    
    # Math: remap da [0,1] a [-1,1]
    remap = add_node(nds, "ShaderNodeMapRange", location=(0, 0))
    remap.inputs["From Min"].default_value = 0.0
    remap.inputs["From Max"].default_value = 1.0
    remap.inputs["To Min"].default_value   = -1.0
    remap.inputs["To Max"].default_value   =  1.0
    
    # Multiply per strength
    mul = add_node(nds, "ShaderNodeMath", location=(200, 0))
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = strength
    
    # Displacement direction
    if direction == 'normal':
        vec_mul = add_node(nds, "ShaderNodeVectorMath", location=(400, 0))
        vec_mul.operation = 'MULTIPLY'
    elif direction == 'z':
        combine = add_node(nds, "ShaderNodeCombineXYZ", location=(400, 0))
        combine.inputs["X"].default_value = 0.0
        combine.inputs["Y"].default_value = 0.0
    else:  # 'xyz'
        noise_v = add_node(nds, "ShaderNodeTexNoise", location=(-200, -300))
        noise_v.noise_dimensions = '3D'
        noise_v.inputs["Scale"].default_value  = scale
        noise_v.inputs["Detail"].default_value = detail
    
    # Set Position
    set_pos = add_node(nds, "GeometryNodeSetPosition", location=(600, 0))
    
    # Collega
    lks.new(pos.outputs[0],             noise.inputs["Vector"])
    lks.new(noise.outputs["Fac"],       remap.inputs["Value"])
    lks.new(remap.outputs[0],           mul.inputs[0])
    lks.new(in_nd.outputs["Strength"],  mul.inputs[1])
    
    if direction == 'normal':
        lks.new(normal.outputs[0],      vec_mul.inputs[0])
        lks.new(mul.outputs[0],         vec_mul.inputs[1])
        lks.new(in_nd.outputs[0],       set_pos.inputs["Geometry"])
        lks.new(vec_mul.outputs[0],     set_pos.inputs["Offset"])
    elif direction == 'z':
        lks.new(mul.outputs[0],         combine.inputs["Z"])
        lks.new(in_nd.outputs[0],       set_pos.inputs["Geometry"])
        lks.new(combine.outputs[0],     set_pos.inputs["Offset"])
    
    lks.new(in_nd.outputs["Scale"],    noise.inputs["Scale"])
    lks.new(set_pos.outputs["Geometry"], out_nd.inputs[0])
    
    return mod, ng
```

---

## PATTERN 4 — Array su curva

Istanzia oggetti equidistanti lungo una curva.
Usato per: recinzioni, binari del treno, grani di una collana,
denti di una sega, anelli di una catena, pilastri di un viadotto.

```python
def array_on_curve(curve_obj, instance_obj, count=20,
                   align_to_curve=True, name="ArrayOnCurve"):
    """
    Dispone instance_obj equidistanti lungo curve_obj.
    
    count         : numero di istanze
    align_to_curve: orienta ogni istanza lungo la tangente della curva
    
    Pipeline: Curve → Resample → Curve to Points → Instance on Points → Output
    
    Esempi:
        # Pali di recinzione
        array_on_curve(fence_path, fence_post, count=30)
        
        # Grani collana
        array_on_curve(necklace_curve, pearl, count=45, align_to_curve=False)
        
        # Colonne su arco
        array_on_curve(arch_curve, column, count=8)
    """
    mod, ng, nds, lks = create_gn_modifier(curve_obj, name)
    for l in list(lks): lks.remove(l)
    
    in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
    out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")
    
    add_group_input(ng, "Count", "NodeSocketInt",
                    default=count, min_val=1, max_val=500)
    
    # Resample Curve (punti equidistanti)
    resample = add_node(nds, "GeometryNodeResampleCurve",
                        location=(0, 0))
    resample.mode = 'COUNT'
    resample.inputs["Count"].default_value = count
    
    # Curve to Points
    c2pts = add_node(nds, "GeometryNodeCurveToPoints",
                     location=(200, 0))
    c2pts.mode = 'COUNT'
    c2pts.inputs["Count"].default_value = count
    
    # Object Info
    obj_info = add_node(nds, "GeometryNodeObjectInfo", location=(0, -200))
    obj_info.inputs["Object"].default_value = instance_obj
    
    # Instance on Points
    inst = add_node(nds, "GeometryNodeInstanceOnPoints", location=(400, 0))
    
    # Realize
    realize = add_node(nds, "GeometryNodeRealizeInstances", location=(600, 0))
    
    lks.new(in_nd.outputs[0],              resample.inputs["Curve"])
    lks.new(in_nd.outputs["Count"],        resample.inputs["Count"])
    lks.new(resample.outputs["Curve"],     c2pts.inputs["Curve"])
    lks.new(in_nd.outputs["Count"],        c2pts.inputs["Count"])
    lks.new(c2pts.outputs["Points"],       inst.inputs["Points"])
    lks.new(obj_info.outputs["Geometry"],  inst.inputs["Instance"])
    if align_to_curve:
        lks.new(c2pts.outputs["Rotation"], inst.inputs["Rotation"])
    lks.new(inst.outputs["Instances"],     realize.inputs["Geometry"])
    lks.new(realize.outputs["Geometry"],   out_nd.inputs[0])
    
    return mod, ng
```

---

## PATTERN 5 — Geometria parametrica pura (senza mesh input)

Costruisce geometria da zero dentro il node group — nessuna mesh di input.

```python
def parametric_grid(obj, x_count=10, y_count=10, spacing=0.1,
                    height_noise=True, name="ParamGrid"):
    """
    Griglia di punti/istanze completamente parametrica.
    
    Esempi:
        # Piastrellatura (con istanze mattoni)
        parametric_grid(empty, x_count=20, y_count=10, spacing=0.25)
        
        # Città procedurale (con istanze edifici)
        parametric_grid(city_base, x_count=8, y_count=8, spacing=1.5,
                        height_noise=True)
    """
    mod, ng, nds, lks = create_gn_modifier(obj, name)
    for l in list(lks): lks.remove(l)
    
    in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
    out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")
    
    add_group_input(ng, "X Count", "NodeSocketInt", default=x_count, min_val=1, max_val=100)
    add_group_input(ng, "Y Count", "NodeSocketInt", default=y_count, min_val=1, max_val=100)
    add_group_input(ng, "Spacing", "NodeSocketFloat", default=spacing, min_val=0.01)
    
    # Mesh Grid come base di punti
    grid = add_node(nds, "GeometryNodeMeshPrimitiveGrid", location=(-200, 0))
    grid.inputs["Size X"].default_value = x_count * spacing
    grid.inputs["Size Y"].default_value = y_count * spacing
    grid.inputs["Vertices X"].default_value = x_count
    grid.inputs["Vertices Y"].default_value = y_count
    
    # Connetti Group Input alla griglia
    lks.new(in_nd.outputs["X Count"], grid.inputs["Vertices X"])
    lks.new(in_nd.outputs["Y Count"], grid.inputs["Vertices Y"])
    lks.new(grid.outputs["Mesh"],     out_nd.inputs[0])
    
    return mod, ng
```

---

## CATALOGO NODI — Tipi più usati

```python
# ── GEOMETRIA BASE ────────────────────────────────────────────
'GeometryNodeMeshPrimitiveSphere'      # UV Sphere: inputs Segments, Rings, Radius
'GeometryNodeMeshPrimitiveCylinder'    # Cilindro: Vertices, Radius, Depth
'GeometryNodeMeshPrimitiveCone'        # Cono: Radius Top/Bottom, Depth
'GeometryNodeMeshPrimitiveCube'        # Cubo: Size
'GeometryNodeMeshPrimitiveGrid'        # Griglia: Size X/Y, Vertices X/Y
'GeometryNodeMeshPrimitiveCircle'      # Cerchio: Vertices, Radius
'GeometryNodeMeshPrimitiveLine'        # Linea: Count, Length
'GeometryNodeCurvePrimitiveCircle'     # Cerchio curva: Resolution, Radius
'GeometryNodeCurvePrimitiveLine'       # Linea curva: Start/End

# ── DISTRIBUZIONE / INSTANZIAZIONE ───────────────────────────
'GeometryNodeDistributePointsOnFaces'  # Scatter su superficie: Density, Seed
'GeometryNodeInstanceOnPoints'         # Istanzia su punti: Instance, Rotation, Scale
'GeometryNodeRealizeInstances'         # Converte istanze in mesh reale
'GeometryNodeRotateInstances'          # Ruota istanze: Rotation, Pivot
'GeometryNodeScaleInstances'           # Scala istanze: Scale, Center

# ── TRASFORMAZIONI ────────────────────────────────────────────
'GeometryNodeSetPosition'              # Sposta vertici: Position, Offset
'GeometryNodeTransform'                # Trasforma oggetto: Translation, Rotation, Scale
'GeometryNodeJoinGeometry'             # Unisce geometrie
'GeometryNodeSeparateGeometry'         # Separa per selezione
'GeometryNodeDeleteGeometry'           # Elimina per selezione

# ── CURVE ────────────────────────────────────────────────────
'GeometryNodeCurveToMesh'              # Curva → Mesh: Profile Curve, Fill Caps
'GeometryNodeCurveToPoints'            # Curva → Punti: Count, Length
'GeometryNodeResampleCurve'            # Ricampiona: Count, Length, Evaluated
'GeometryNodeFillCurve'                # Riempi curva chiusa → mesh
'GeometryNodeSetCurveRadius'           # Imposta spessore curva
'GeometryNodeSetSplineCyclic'          # Chiude la curva
'GeometryNodeSplineParameter'          # Factor [0-1] lungo la curva (utile per taper)

# ── MESH OPERATIONS ──────────────────────────────────────────
'GeometryNodeSubdivisionSurface'       # Subdivision: Level
'GeometryNodeExtrudeMesh'              # Estrude: Offset, Offset Scale
'GeometryNodeMeshBoolean'              # Boolean: DIFFERENCE / UNION / INTERSECT
'GeometryNodeFlipFaces'                # Inverti normali
'GeometryNodeScaleElements'            # Scala face/edge
'GeometryNodeSetShadeSmooth'           # Shade smooth

# ── INPUT ─────────────────────────────────────────────────────
'GeometryNodeInputPosition'            # Posizione vertice (Vector)
'GeometryNodeInputNormal'              # Normale vertice (Vector)
'GeometryNodeInputIndex'               # Indice vertice (Int)
'NodeGroupInput'                       # Ingresso del group
'NodeGroupOutput'                      # Uscita del group

# ── UTILITÀ ──────────────────────────────────────────────────
'GeometryNodeObjectInfo'               # Geometria/posizione di un oggetto esterno
'GeometryNodeCollectionInfo'           # Geometria di una collezione
'GeometryNodeConvexHull'               # Inviluppo convesso
'GeometryNodeBoundBox'                 # Bounding box

# ── MATH ─────────────────────────────────────────────────────
'ShaderNodeMath'                       # Math: ADD, SUBTRACT, MULTIPLY, DIVIDE, POWER...
'ShaderNodeVectorMath'                 # Vector Math: ADD, DOT_PRODUCT, CROSS_PRODUCT...
'ShaderNodeMapRange'                   # Remap [in_min,in_max] → [out_min,out_max]
'ShaderNodeTexNoise'                   # Noise 3D: Scale, Detail, Roughness
'ShaderNodeTexWave'                    # Wave: Bands/Rings, Scale, Distortion
'ShaderNodeSeparateXYZ'                # Separa Vector → X, Y, Z
'ShaderNodeCombineXYZ'                 # Combina X, Y, Z → Vector
'FunctionNodeRandomValue'              # Valore casuale: INT, FLOAT, FLOAT_VECTOR, BOOL
'GeometryNodeInputID'                  # ID elemento (per seed per-istanza)
```

---

## ACCESSO AI SOCKET — Guida rapida

```python
# Lettura output disponibili di un nodo:
for i, out in enumerate(node.outputs):
    print(i, out.name, out.bl_idname)

# Lettura input disponibili:
for i, inp in enumerate(node.inputs):
    print(i, inp.name, inp.bl_idname)

# Impostare un valore di input (quando non collegato):
node.inputs["Density"].default_value = 500.0
node.inputs["Scale"].default_value   = 1.0
node.inputs["Seed"].default_value    = 42

# Link per nome (preferito — più leggibile):
links.new(dist.outputs["Points"],     inst.inputs["Points"])
links.new(dist.outputs["Normal"],     inst.inputs["Rotation"])

# Link per indice (quando il nome è ambiguo o non noto):
links.new(in_node.outputs[0], set_pos.inputs[0])

# ATTENZIONE — socket duplicati (es. GeometryNodeJoinGeometry):
# Join ha UN SOLO input "Geometry" ma accetta più connessioni
# Blender gestisce automaticamente la lista interna
links.new(source_a.outputs["Geometry"], join.inputs["Geometry"])
links.new(source_b.outputs["Geometry"], join.inputs["Geometry"])  # aggiunge al multi-input
```

---

## APPLICARE UN MODIFIER GeoNodes

```python
def apply_gn(obj, modifier_name=None):
    """
    Applica (rende definitivo) il modifier Geometry Nodes.
    Dopo: la mesh è modificata in modo permanente, il modifier è rimosso.
    
    ATTENZIONE: operazione distruttiva. Usa solo per il risultato finale.
    Per mantenere la parametricità, lascia il modifier attivo.
    """
    bpy.context.view_layer.objects.active = obj
    
    if modifier_name:
        mod = obj.modifiers.get(modifier_name)
    else:
        mod = next((m for m in obj.modifiers if m.type == 'NODES'), None)
    
    if mod:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    
    return obj
```

---

## ESEMPIO COMPLETO — Erba su terreno

```python
import bpy, math

# ── 1. Terreno ──────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_grid_add(x_subdivisions=50, y_subdivisions=50,
    size=4.0, location=(0, 0, 0))
terrain = bpy.context.active_object
terrain.name = "Terrain"

# Deforma con noise (usa il pattern noise_deform)
# ... oppure direttamente in GeoNodes:
noise_deform(terrain, scale=3.0, strength=0.12, direction='z', name="TerrainNoise")

# ── 2. Filo d'erba (istanza) ────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=0.02, location=(100, 0, 0))
blade = bpy.context.active_object
blade.name = "GrassBlade"
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=4)
bpy.ops.object.mode_set(mode='OBJECT')
# Piega il filo verso l'alto
for v in blade.data.vertices:
    t = (v.co.y + 0.01) / 0.02   # 0 = base, 1 = punta
    v.co.z = t * 0.08              # altezza max 8cm
    v.co.y = 0
blade.data.update()
blade.data.shade_smooth()

# ── 3. Scatter ──────────────────────────────────────────────────────────────
scatter_on_surface(terrain, blade,
    density=800,
    random_rotation=True,
    align_to_normal=True,
    scale_min=0.6, scale_max=1.4,
    seed=7,
    name="GrassScatter")
```

---

## ESEMPIO COMPLETO — Sprinkles su donut (pattern reale)

```python
import bpy

# Assumendo che icing e sprinkle_base esistano in scena
icing  = bpy.data.objects["Icing"]
sprink = bpy.data.objects["Sprinkle"]

mod, ng, nds, lks = create_gn_modifier(icing, "Sprinkles_GN")
for l in list(lks): lks.remove(l)

in_nd  = next(n for n in nds if n.bl_idname == "NodeGroupInput")
out_nd = next(n for n in nds if n.bl_idname == "NodeGroupOutput")

# Distribute
dist = add_node(nds, "GeometryNodeDistributePointsOnFaces",
                location=(0,0), inputs={"Density": 3000.0})
dist.distribute_method = "RANDOM"

# Object Info
obj_info = add_node(nds, "GeometryNodeObjectInfo", location=(0,-200))
obj_info.inputs["Object"].default_value = sprink

# Instance
inst = add_node(nds, "GeometryNodeInstanceOnPoints", location=(300,0))

# Random rotation
rand_rot = add_node(nds, "FunctionNodeRandomValue", location=(0,-400))
rand_rot.data_type = "FLOAT_VECTOR"
rand_rot.inputs["Min"].default_value = (0, 0, 0)
rand_rot.inputs["Max"].default_value = (6.2832, 6.2832, 6.2832)

rot  = add_node(nds, "GeometryNodeRotateInstances",   location=(500,0))
real = add_node(nds, "GeometryNodeRealizeInstances",  location=(700,0))
join = add_node(nds, "GeometryNodeJoinGeometry",      location=(900,0))

lks.new(in_nd.outputs[0],           dist.inputs["Mesh"])
lks.new(dist.outputs["Points"],     inst.inputs["Points"])
lks.new(obj_info.outputs["Geometry"], inst.inputs["Instance"])
lks.new(dist.outputs["Normal"],     inst.inputs["Rotation"])
lks.new(inst.outputs["Instances"],  rot.inputs["Instances"])
lks.new(rand_rot.outputs[0],        rot.inputs["Rotation"])
lks.new(rot.outputs["Instances"],   real.inputs["Geometry"])
lks.new(in_nd.outputs[0],          join.inputs["Geometry"])
lks.new(real.outputs["Geometry"],  join.inputs["Geometry"])
lks.new(join.outputs["Geometry"],  out_nd.inputs[0])
```

---

## REGOLE QUALITÀ

1. **`ng.interface.new_socket()`** — NON `ng.inputs.new()` / `ng.outputs.new()`.
   Quelle API sono deprecate da Blender 4.0. Usa sempre `interface`.

2. **OUTPUT prima di INPUT** nell'interfaccia:
   ```python
   ng.interface.new_socket("Geometry", in_out="OUTPUT", ...)
   ng.interface.new_socket("Geometry", in_out="INPUT",  ...)
   ```
   L'ordine sbagliato causa IndexError al momento del link.

3. **Rimuovi il link pass-through** prima di costruire il grafo:
   ```python
   for l in list(ng.links): ng.links.remove(l)
   ```
   Il `create_gn_modifier` aggiunge un link Geometry→Output di default.

4. **`RealizeInstances` prima del Join** — istanze non realizzate
   non possono essere joininate con `JoinGeometry`.

5. **`transform_space = 'ORIGINAL'`** su `GeometryNodeObjectInfo`
   per preservare la scala dell'istanza (senza 'ORIGINAL' scala tutto a 1).

6. **Verifica socket per nome** — gli indici cambiano tra versioni:
   ```python
   for i, out in enumerate(node.outputs): print(i, out.name)
   ```

7. **Group Input accedibili per nome** dopo `add_group_input`:
   `in_node.outputs["Density"]` — funziona se il nome corrisponde esattamente.

---

## ANALISI RICHIESTA

| Keyword | Pattern |
|---------|---------|
| `scatter / distribuisci / spargi` | `scatter_on_surface` |
| `erba / foglie / pietre / sprinkles` | `scatter_on_surface` |
| `tubo / cavo / pipe su curva` | `curve_to_pipe` |
| `cornice / binario / profilo` | `curve_to_profile` |
| `recinzione / colonne / array su percorso` | `array_on_curve` |
| `deformazione / noise / ondulato` | `noise_deform` |
| `griglia / piastrelle / pattern` | `parametric_grid` |
| `parametrico / slider / non-distruttivo` | Group Input |
| `istanziazione / GPU / tanti oggetti` | Instance on Points |
| `applica / rendi definitivo` | `apply_gn` |

**Se richiesta ambigua → chiedi: "La geometria deve rimanere parametrica
(modifier) o è definitiva? Quante istanze prevedi (< 50 = bmesh, > 50 = GeoNodes)?"**

## Output

- Codice Python completo, nessun placeholder
- Sempre: `create_gn_modifier` → rimuovi link → costruisci grafo
- Group Input per ogni parametro che l'utente vorrà regolare
- Dopo esecuzione: screenshot → verifica grafo in Blender → itera
- Per scatter: include sempre `JoinGeometry` per mantenere la mesh host
