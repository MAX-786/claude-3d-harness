---
description: >
  Skill per materiali, texture e UV in Blender. Copre: materiali Principled BSDF
  procedurali (noise, bump, SSS, Fresnel), UV unwrap (Smart Project, angolo-based,
  manuale), baking AO/Normal/Diffuse su immagine, texture painting via vertex paint
  o image stamp, PBR workflow con immagini reali (albedo + roughness + normal map).
  Usa questa skill quando devi assegnare materiali realistici, fare baking, UV unwrap,
  o costruire un node tree di materiale complesso da zero.
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
---

# Skill: Blender Texture & Materials

Sei un esperto di materiali e texturing in Blender con `bpy` + node tree.
Ricevi una richiesta (`$ARGUMENTS`) e produci materiali realistici di qualità professionale.

---

## Connessione — MCP (predefinito) + HTTP (fallback)

**MCP (porta 9876 — PREFERITO):**
```python
mcp__Blender__execute_blender_code(code="import bpy\n# ...\nresult={'ok':True}")
mcp__Blender__get_screenshot_of_window_as_image()
mcp__Blender__render_viewport_to_path(output_path="C:/Users/josia/Downloads/out.png")
```

**HTTP fallback (porta 7234):**
```python
import urllib.request, json
def blender(code, timeout=60):
    data = json.dumps({"code": code, "timeout": timeout}).encode()
    req  = urllib.request.Request("http://localhost:7234/execute", data=data,
                                  headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout+10).read())
    if "error" in r: raise RuntimeError(r["error"])
    return r.get("ok")
```

---

## Helper universali (copia nel blocco che esegui)

```python
import bpy

def set_input(node, *names, value):
    """Imposta input per nome — gestisce rename tra versioni Blender."""
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return True
    return False

def link(links, from_node, from_sock, to_node, to_sock):
    links.new(from_node.outputs[from_sock], to_node.inputs[to_sock])

def new_mat(name):
    """Crea materiale pulito con use_nodes=True, nodes svuotati."""
    if name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[name])
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat, mat.node_tree.nodes, mat.node_tree.links

def apply_mat(obj_name, mat):
    """Assegna mat allo slot 0 dell'oggetto."""
    ob = bpy.data.objects.get(obj_name)
    if ob:
        ob.data.materials.clear()
        ob.data.materials.append(mat)
```

---

## Sezione 1 — UV Unwrap

### 1.1 Smart UV Project (raccomandato per oggetti complessi)
```python
import bpy

def smart_uv(obj_name, angle_limit=66, margin=0.02):
    ob = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(
        angle_limit   = angle_limit,
        island_margin = margin,
        scale_to_bounds = True
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = ob.data.uv_layers.active
    return uv.name if uv else None
```

### 1.2 Angle-Based Unwrap (superfici organiche)
```python
def unwrap_angle(obj_name, margin=0.02):
    ob = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Mark seam automatico prima di unwrap
    bpy.ops.mesh.mark_seam(clear=True)  # rimuovi seam precedenti
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
```

### 1.3 Cube Projection (muri, pavimenti, superfici piane)
```python
def cube_project(obj_name, cube_size=1.0):
    ob = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=cube_size)
    bpy.ops.object.mode_set(mode='OBJECT')
```

### 1.4 UV Layer aggiuntivo (baking separato)
```python
def add_uv_layer(obj_name, name="UVBake"):
    ob = bpy.data.objects[obj_name]
    ob.data.uv_layers.new(name=name)
    ob.data.uv_layers.active = ob.data.uv_layers[name]
    # Fai unwrap con Smart Project su questo layer
    smart_uv(obj_name)
```

---

## Sezione 2 — Materiali Procedurali

### TABELLA VALORI DI RIFERIMENTO — Materiali Comuni

> **Regola:** Metallic è sempre 0 o 1 — nessun valore intermedio (le cose sono o metallo o non-metallo).
> **Regola:** Mai Base Color = (0,0,0) puro. Anche i materiali più scuri riflettono qualcosa. Minimo: 0.02–0.03.

| Materiale | Base Color (lineare) | Roughness | Metallic | Specular IOR | Note |
|-----------|---------------------|-----------|----------|--------------|------|
| Plastica matte nera | (0.025, 0.025, 0.030) | 0.50–0.65 | 0 | 0.25 | + noise su roughness |
| Plastica semi-gloss | (0.03, 0.03, 0.04) | 0.35–0.50 | 0 | 0.30 | consumer electronics |
| Vetro screen (spento) | (0.005, 0.006, 0.012) | 0.01–0.03 | 0 | 0.50 | quasi mirror |
| Porcellana bianca | (0.955, 0.940, 0.896) | 0.08–0.12 | 0 | 0.55 | coat 0.2 |
| Legno chiaro | (0.55, 0.38, 0.22) | 0.65–0.80 | 0 | 0.10 | + grain texture |
| Legno scuro | (0.12, 0.07, 0.04) | 0.70–0.85 | 0 | 0.10 | + grain texture |
| Metallo lucido | (0.95, 0.95, 0.95) | 0.05–0.15 | 1 | — | alluminio, acciaio |
| Metallo spazzolato | (0.80, 0.80, 0.80) | 0.30–0.45 | 1 | — | + anisotropy |
| Oro | (1.00, 0.78, 0.28) | 0.10–0.25 | 1 | — | colore giallo caldo |
| Gomma | (0.02, 0.02, 0.02) | 0.90–1.00 | 0 | 0.05 | molto matte |
| Vetro trasparente | (0.92, 0.95, 0.98) | 0.00–0.05 | 0 | 0.50 | transmission=1, IOR=1.52 |
| Carta | (0.85, 0.83, 0.78) | 0.90–1.00 | 0 | 0.05 | no specular |
| Tessuto cotone | (base a scelta) | 0.85–0.95 | 0 | 0.05 | + fuzz/sheen |
| Pelle umana | (0.77, 0.52, 0.40) | 0.60–0.75 | 0 | 0.35 | SSS obbligatorio |

---

### Pattern noise-roughness — Anti "CG-Clean Look"

La roughness uniforme è il segnale più riconoscibile del "CG pulito". Aggiungere micro-variazione con Noise Texture rompe l'uniformità sintetica e rende qualsiasi superficie più reale.

```python
def add_roughness_noise(nodes, links, bsdf,
                        base_roughness=0.50,
                        variation=0.08,
                        scale=80.0,
                        detail=4.0):
    """
    Aggiunge micro-variazione di roughness tramite Noise → ColorRamp → Roughness.

    base_roughness: valore centrale (es. 0.50 per plastica matte)
    variation:      ±variazione attorno alla base (0.05–0.10 è sottile, 0.15+ è visibile)
    scale:          frequenza spaziale del noise (60–120 per micro-texture, 5–20 per macro)
    detail:         ottave del noise (2–4 per plastica, 6–8 per roccia)

    Esempi:
      Plastica matte:    base=0.50, variation=0.08, scale=80
      Plastica semi-gloss: base=0.40, variation=0.05, scale=100
      Legno:             base=0.70, variation=0.15, scale=20, detail=6
      Metallo spazzolato: base=0.35, variation=0.10, scale=60
    """
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value    = scale
    noise.inputs["Detail"].default_value   = detail
    noise.inputs["Roughness"].default_value = 0.6
    noise.inputs["Distortion"].default_value = 0.0
    noise.location = (-400, -200)

    ramp = nodes.new("ShaderNodeValToRGB")
    lo = max(0.0, base_roughness - variation)
    hi = min(1.0, base_roughness + variation)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color    = (lo, lo, lo, 1.0)
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color    = (hi, hi, hi, 1.0)
    ramp.location = (-200, -200)

    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    return noise, ramp


# Uso rapido su un materiale esistente:
def apply_roughness_noise_to(mat, base_roughness=0.50, variation=0.08, scale=80.0):
    """Aggiunge noise-roughness a un materiale già esistente."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        add_roughness_noise(nt.nodes, nt.links, bsdf,
                            base_roughness, variation, scale)
```

---

### Pattern base: Principled BSDF
```python
mat, nodes, links = new_mat("MyMat")

out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (200, 0)
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

bsdf.inputs["Base Color"].default_value  = (0.8, 0.3, 0.1, 1.0)
bsdf.inputs["Roughness"].default_value   = 0.6
bsdf.inputs["Metallic"].default_value    = 0.0
set_input(bsdf, "Specular IOR Level", "Specular", value=0.5)

# Per plastica: aggiungi subito noise-roughness
add_roughness_noise(nodes, links, bsdf, base_roughness=0.5, variation=0.08)
```

### 2.1 mat_porcelain — Porcellana / Ceramica
```python
def mat_porcelain(name="Porcelain", color=(0.955, 0.940, 0.896)):
    mat, nodes, links = new_mat(name)
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (200, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Micro-variazione noise (2%) via ShaderNodeMix RGBA
    noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-400, 100)
    noise.inputs["Scale"].default_value    = 12.0
    noise.inputs["Detail"].default_value   = 2.0
    noise.inputs["Roughness"].default_value= 0.5

    mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.location = (-100, 100)
    mix.inputs[6].default_value = (*[c * 0.97 for c in color], 1.0)  # scuro
    mix.inputs[7].default_value = (*[c * 1.01 for c in color], 1.0)  # chiaro
    links.new(noise.outputs["Fac"], mix.inputs[0])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.08
    set_input(bsdf, "IOR", value=1.52)
    set_input(bsdf, "Coat Weight", "Clearcoat", value=0.2)
    set_input(bsdf, "Coat Roughness", "Clearcoat Roughness", value=0.05)
    set_input(bsdf, "Specular IOR Level", "Specular", value=0.55)
    return mat

# NOTA ShaderNodeMix RGBA:
#   inputs[0]  = Factor (Fac)
#   inputs[6]  = Color A  (NON inputs[1])
#   inputs[7]  = Color B  (NON inputs[2])
#   outputs[2] = risultato Color  (NON outputs[0])
# ShaderNodeMixRGB è DEPRECATO in Blender 4.x/5.x — non usare.
```

### 2.2 mat_organic — Materiale organico con SSS + Noise + Fresnel
```python
def mat_organic(name="Organic",
                base_color=(0.65, 0.05, 0.05),
                roughness_range=(0.50, 0.72),
                sss=0.18, sss_radius=(0.92, 0.10, 0.10),
                bump_strength=0.35, bump_dist=0.008,
                glossy_ior=1.38, glossy_rough=0.06):
    """
    Stack: Noise→ColorRamp→Principled + Noise→Bump + Glossy→Fresnel→Mix
    Usato per: muscoli, frutta, skin, radici, tessuti biologici.
    """
    mat, nodes, links = new_mat(name)

    # Coordinate
    tc  = nodes.new("ShaderNodeTexCoord"); tc.location = (-1100, 0)
    mp  = nodes.new("ShaderNodeMapping");  mp.location = (-900, 0)
    mp.inputs["Scale"].default_value = (1.2, 1.2, 1.0)
    links.new(tc.outputs["Object"], mp.inputs["Vector"])

    # Noise colore
    nc = nodes.new("ShaderNodeTexNoise"); nc.location = (-680, 250)
    nc.inputs["Scale"].default_value     = 6.0
    nc.inputs["Detail"].default_value    = 5.0
    nc.inputs["Roughness"].default_value = 0.65
    nc.inputs["Distortion"].default_value= 0.25
    links.new(mp.outputs["Vector"], nc.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB"); ramp.location = (-430, 250)
    try:    ramp.color_ramp.color_space = "RGB"
    except: ramp.color_ramp.color_mode  = "RGB"   # Blender 5.x rinomina
    c = base_color
    ramp.color_ramp.elements[0].color = (c[0]*0.55, c[1]*0.55, c[2]*0.55, 1.0)
    ramp.color_ramp.elements[1].color = (*c, 1.0)
    links.new(nc.outputs["Fac"], ramp.inputs["Fac"])

    # Noise rugosità
    nr = nodes.new("ShaderNodeTexNoise"); nr.location = (-680, -50)
    nr.inputs["Scale"].default_value = 18.0
    links.new(mp.outputs["Vector"], nr.inputs["Vector"])
    rr = nodes.new("ShaderNodeValToRGB"); rr.location = (-430, -50)
    rr.color_ramp.elements[0].color = (*[roughness_range[0]]*3, 1.0)
    rr.color_ramp.elements[1].color = (*[roughness_range[1]]*3, 1.0)
    links.new(nr.outputs["Fac"], rr.inputs["Fac"])

    # Bump
    nb = nodes.new("ShaderNodeTexNoise"); nb.location = (-680, -350)
    nb.inputs["Scale"].default_value     = 22.0
    nb.inputs["Detail"].default_value    = 8.0
    nb.inputs["Roughness"].default_value = 0.55
    links.new(mp.outputs["Vector"], nb.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump"); bump.location = (-180, -300)
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = bump_dist
    links.new(nb.outputs["Fac"], bump.inputs["Height"])

    # Principled BSDF
    bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (80, 120)
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(rr.outputs["Color"],   bsdf.inputs["Roughness"])
    links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
    set_input(bsdf, "Subsurface Weight", "Subsurface", value=sss)
    try:    bsdf.inputs["Subsurface Radius"].default_value = sss_radius
    except: pass
    set_input(bsdf, "Specular IOR Level", "Specular", value=0.28)

    # Glossy (strato umido)
    glossy = nodes.new("ShaderNodeBsdfGlossy"); glossy.location = (80, -200)
    glossy.inputs["Roughness"].default_value = glossy_rough
    links.new(bump.outputs["Normal"], glossy.inputs["Normal"])

    # Fresnel → Mix
    fresnel = nodes.new("ShaderNodeFresnel"); fresnel.location = (80, -380)
    fresnel.inputs["IOR"].default_value = glossy_ior
    mix = nodes.new("ShaderNodeMixShader"); mix.location = (380, 0)
    links.new(fresnel.outputs["Fac"],   mix.inputs["Fac"])
    links.new(bsdf.outputs["BSDF"],     mix.inputs[1])
    links.new(glossy.outputs["BSDF"],   mix.inputs[2])

    out = nodes.new("ShaderNodeOutputMaterial"); out.location = (620, 0)
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat
```

### 2.3 mat_metal — Metallo PBR
```python
def mat_metal(name="Metal", color=(0.8, 0.8, 0.85), roughness=0.15):
    mat, nodes, links = new_mat(name)
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (0, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bsdf.inputs["Base Color"].default_value  = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value    = 1.0
    bsdf.inputs["Roughness"].default_value   = roughness
    set_input(bsdf, "Specular IOR Level", "Specular", value=0.5)

    # Anisotropia leggera per look brushed
    if "Anisotropic" in bsdf.inputs:
        bsdf.inputs["Anisotropic"].default_value = 0.3
    return mat
```

### 2.4 mat_glass — Vetro
```python
def mat_glass(name="Glass", color=(0.95, 0.98, 1.0), roughness=0.02, ior=1.45):
    mat, nodes, links = new_mat(name)
    mat.blend_method = "BLEND"  # Eevee transparency
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (0, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bsdf.inputs["Base Color"].default_value  = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value   = roughness
    set_input(bsdf, "IOR", value=ior)
    set_input(bsdf, "Transmission Weight", "Transmission", value=1.0)
    return mat
```

### 2.5 mat_leather — Cuoio / Pelle
```python
def mat_leather(name="Leather", color=(0.25, 0.10, 0.05), roughness=0.75):
    mat, nodes, links = new_mat(name)
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (200, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Voronoi per pori del cuoio
    vc = nodes.new("ShaderNodeTexVoronoi"); vc.location = (-500, 200)
    vc.inputs["Scale"].default_value    = 80.0
    vc.inputs["Randomness"].default_value = 0.8
    noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-500, -100)
    noise.inputs["Scale"].default_value = 12.0
    noise.inputs["Detail"].default_value = 6.0

    # Mix Voronoi + Noise per bump complesso
    mix_h = nodes.new("ShaderNodeMix"); mix_h.data_type = "FLOAT"
    mix_h.location = (-200, 100); mix_h.inputs[0].default_value = 0.4
    links.new(vc.outputs["Distance"],   mix_h.inputs[4])  # A (float)
    links.new(noise.outputs["Fac"],     mix_h.inputs[5])  # B (float)

    bump = nodes.new("ShaderNodeBump"); bump.location = (-20, 0)
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.003
    links.new(mix_h.outputs[1], bump.inputs["Height"])  # output[1] = float

    # Colore con leggera variazione noise
    cr = nodes.new("ShaderNodeValToRGB"); cr.location = (-200, -200)
    cr.color_ramp.elements[0].color = (*[c*0.7 for c in color], 1.0)
    cr.color_ramp.elements[1].color = (*color, 1.0)
    links.new(noise.outputs["Fac"], cr.inputs["Fac"])

    links.new(cr.outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = roughness
    set_input(bsdf, "Sheen Weight", "Sheen", value=0.08)
    return mat
```

### 2.6 mat_emission — Materiale emissivo (luce, LED, neon)
```python
def mat_emission(name="Emission", color=(1.0, 0.9, 0.7), strength=5.0):
    mat, nodes, links = new_mat(name)
    out = nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    em  = nodes.new("ShaderNodeEmission");       em.location  = (0, 0)
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    em.inputs["Color"].default_value    = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    return mat
```

### 2.7 mat_wood — Legno procedurale
```python
def mat_wood(name="Wood", ring_color=(0.38, 0.20, 0.08), grain_color=(0.55, 0.30, 0.12)):
    mat, nodes, links = new_mat(name)
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (700, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (350, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord"); tc.location = (-900, 0)
    mp = nodes.new("ShaderNodeMapping");  mp.location = (-700, 0)
    links.new(tc.outputs["Object"], mp.inputs["Vector"])

    # Wave per anelli del legno
    wave = nodes.new("ShaderNodeTexWave"); wave.location = (-500, 100)
    wave.wave_type    = "RINGS"
    wave.inputs["Scale"].default_value      = 8.0
    wave.inputs["Distortion"].default_value = 2.5
    wave.inputs["Detail"].default_value     = 6.0
    wave.inputs["Detail Roughness"].default_value = 0.65
    links.new(mp.outputs["Vector"], wave.inputs["Vector"])

    cr = nodes.new("ShaderNodeValToRGB"); cr.location = (-200, 100)
    cr.color_ramp.elements[0].color = (*ring_color,  1.0)
    cr.color_ramp.elements[1].color = (*grain_color, 1.0)
    links.new(wave.outputs["Fac"], cr.inputs["Fac"])

    # Noise per venature casuali
    noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-500, -150)
    noise.inputs["Scale"].default_value = 25.0
    noise.inputs["Detail"].default_value = 8.0
    links.new(mp.outputs["Vector"], noise.inputs["Vector"])

    bump = nodes.new("ShaderNodeBump"); bump.location = (100, -200)
    bump.inputs["Strength"].default_value = 0.15
    links.new(noise.outputs["Fac"], bump.inputs["Height"])

    links.new(cr.outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.55
    set_input(bsdf, "Specular IOR Level", "Specular", value=0.1)
    return mat
```

---

## Sezione 3 — Image Texture (PBR con immagini reali)

### 3.1 Carica immagine e assegna
```python
def mat_image_texture(name, albedo_path, normal_path=None,
                      roughness_path=None, ao_path=None):
    """
    PBR completo con immagini reali.
    Percorsi assoluti, es: "D:/textures/brick_albedo.png"
    """
    mat, nodes, links = new_mat(name)
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (800, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (400, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord"); tc.location = (-900, 0)
    mp = nodes.new("ShaderNodeMapping");  mp.location = (-700, 0)
    links.new(tc.outputs["UV"], mp.inputs["Vector"])

    x = -400

    # Albedo
    if albedo_path:
        img_alb = bpy.data.images.load(albedo_path, check_existing=True)
        n_alb = nodes.new("ShaderNodeTexImage"); n_alb.location = (x, 300)
        n_alb.image = img_alb
        n_alb.image.colorspace_settings.name = "sRGB"
        links.new(mp.outputs["Vector"], n_alb.inputs["Vector"])
        links.new(n_alb.outputs["Color"], bsdf.inputs["Base Color"])

    # Roughness (Linear)
    if roughness_path:
        img_r = bpy.data.images.load(roughness_path, check_existing=True)
        n_r = nodes.new("ShaderNodeTexImage"); n_r.location = (x, 0)
        n_r.image = img_r
        n_r.image.colorspace_settings.name = "Non-Color"
        links.new(mp.outputs["Vector"], n_r.inputs["Vector"])
        links.new(n_r.outputs["Color"], bsdf.inputs["Roughness"])

    # Normal Map
    if normal_path:
        img_n = bpy.data.images.load(normal_path, check_existing=True)
        n_n = nodes.new("ShaderNodeTexImage"); n_n.location = (x, -300)
        n_n.image = img_n
        n_n.image.colorspace_settings.name = "Non-Color"
        nm = nodes.new("ShaderNodeNormalMap"); nm.location = (x+300, -300)
        links.new(mp.outputs["Vector"], n_n.inputs["Vector"])
        links.new(n_n.outputs["Color"], nm.inputs["Color"])
        links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

    # AO (moltiplicato al Base Color)
    if ao_path:
        img_ao = bpy.data.images.load(ao_path, check_existing=True)
        n_ao = nodes.new("ShaderNodeTexImage"); n_ao.location = (x, 600)
        n_ao.image = img_ao
        n_ao.image.colorspace_settings.name = "Non-Color"
        mix_ao = nodes.new("ShaderNodeMix"); mix_ao.data_type = "RGBA"
        mix_ao.blend_type = "MULTIPLY"; mix_ao.location = (x+300, 400)
        mix_ao.inputs[0].default_value = 1.0
        if albedo_path:
            links.new(n_alb.outputs["Color"], mix_ao.inputs[6])
        links.new(n_ao.outputs["Color"],  mix_ao.inputs[7])
        links.new(mix_ao.outputs[2],      bsdf.inputs["Base Color"])

    return mat

# Colorspace regola:
#   Albedo, Diffuse, colori     → "sRGB"
#   Normal, Roughness, AO, Mask → "Non-Color"
```

### 3.2 Tiling / UV Scale via Mapping node
```python
def set_uv_tiling(mat_name, scale=(4.0, 4.0, 1.0)):
    """Scala le UV del materiale via nodo Mapping."""
    mat = bpy.data.materials[mat_name]
    for node in mat.node_tree.nodes:
        if node.type == "MAPPING":
            node.inputs["Scale"].default_value = scale
            break
```

---

## Sezione 4 — Baking

### 4.1 Baking setup e esecuzione
```python
def bake_texture(obj_name, bake_type="AO",
                 width=1024, height=1024,
                 img_name="BakedAO", save_path=None):
    """
    Bake di un singolo tipo su immagine.
    bake_type: "AO", "DIFFUSE", "NORMAL", "SHADOW", "EMIT", "COMBINED"

    Prerequisiti: UV layer attivo, Cycles renderer.
    """
    import bpy
    ob = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = ob
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64  # basso per bake rapido

    # Crea immagine target
    if img_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[img_name])
    img = bpy.data.images.new(img_name, width, height)
    img.generated_color = (0.0, 0.0, 0.0, 1.0)

    # Aggiungi nodo Image Texture al materiale, collegato ma non usato per render
    for mat_slot in ob.material_slots:
        mat = mat_slot.material
        if mat and mat.use_nodes:
            nt = mat.node_tree
            tex_node = nt.nodes.new("ShaderNodeTexImage")
            tex_node.image = img
            tex_node.name  = "__bake_target__"
            # Selezionalo come target
            nt.nodes.active = tex_node

    # Bake
    bpy.ops.object.bake(type=bake_type, use_clear=True)

    # Salva (opzionale)
    if save_path:
        img.filepath_raw = save_path
        img.file_format  = "PNG"
        img.save()

    return img

# Note baking:
# - Cycles OBBLIGATORIO (Eevee non supporta bake)
# - UV layer corretto deve essere ATTIVO prima del bake
# - COMBINED include AO + diffuse + speculare + shadows
# - Per bake su low-poly da high-poly: seleziona prima hi, poi lo (Ctrl+Click),
#   attiva "Selected to Active" nelle impostazioni bake
```

### 4.2 Bake AO completo (pattern consigliato)
```python
def full_ao_bake(obj_name, res=2048, save_path="D:/output/ao.png"):
    """AO bake con impostazioni ottimizzate, salvataggio automatico."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 128
    sc.cycles.bake_type = "AO"

    img = bake_texture(obj_name, "AO", res, res, f"{obj_name}_AO", save_path)
    print(f"AO baked: {save_path}")
    return img
```

### 4.3 Bake Normal Map (high-poly → low-poly)
```python
def bake_normal_hp_to_lp(high_name, low_name,
                          res=2048, extrusion=0.02, save_path="D:/output/normal.png"):
    """
    Bake normal map da high-poly a low-poly.
    Estrusion: distanza di offset per il ray (default 2cm in BU).
    """
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 16  # normal map non ha bisogno di molti samples

    # Seleziona: prima hi, poi lo (lo è active)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects[high_name].select_set(True)
    lo = bpy.data.objects[low_name]
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo

    img = bake_texture(low_name, "NORMAL", res, res, f"{low_name}_Normal", save_path)

    # Configura selected-to-active
    bpy.context.scene.render.bake.use_selected_to_active = True
    bpy.context.scene.render.bake.cage_extrusion = extrusion
    bpy.ops.object.bake(type="NORMAL", use_clear=True)

    if save_path:
        img.filepath_raw = save_path
        img.file_format  = "PNG"
        img.save()
    return img
```

---

## Sezione 5 — Texture Painting (Vertex + Image Stamp)

### 5.1 Vertex Paint
```python
def vertex_paint_base(obj_name, color=(0.8, 0.3, 0.1, 1.0)):
    """
    Inizializza Vertex Paint con colore di base su tutto l'oggetto.
    Usa bpy.ops.paint per fill — richiede active object.
    """
    ob = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='VERTEX_PAINT')

    # Colore tool
    bpy.context.tool_settings.vertex_paint.brush.color = color[:3]

    # Fill di tutto l'oggetto
    bpy.ops.paint.vertex_color_set()  # colora tutti i vertici con il colore brush
    bpy.ops.object.mode_set(mode='OBJECT')

def use_vertex_color_in_mat(obj_name, mat_name="VColMat"):
    """Materiale che legge il vertex color tramite Attribute node."""
    mat, nodes, links = new_mat(mat_name)
    out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (0, 0)
    attr = nodes.new("ShaderNodeVertexColor");     attr.location = (-300, 0)
    # Blender 4.x: attr.layer_name, Blender 5.x: attr.attribute_name (usa entrambi)
    try:    attr.layer_name = "Col"
    except: attr.attribute_name = "Col"
    links.new(attr.outputs["Color"],  bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"],   out.inputs["Surface"])
    apply_mat(obj_name, mat)
```

### 5.2 Image Stamp (pennellata programmatica)
```python
def stamp_image_texture(obj_name, res=1024, base_color=(0.8, 0.5, 0.2)):
    """
    Crea immagine per texture paint con colore base piatto.
    Sostituisce la texture painting manuale: crea img, assegna al materiale.
    """
    img_name = f"{obj_name}_Paint"
    if img_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[img_name])
    img = bpy.data.images.new(img_name, res, res)
    # Fill uniforme
    pixels = [v for _ in range(res * res) for v in (*base_color, 1.0)]
    img.pixels = pixels

    # Assegna al materiale tramite nodo Image Texture
    ob = bpy.data.objects[obj_name]
    if ob.data.materials:
        mat = ob.data.materials[0]
        nt = mat.node_tree
        for n in nt.nodes:
            if n.type == "TEX_IMAGE":
                n.image = img
                break
    return img
```

---

## Sezione 6 — Scene & Render Setup

### 6.1 Setup rapido Cycles
```python
def setup_cycles(samples=128, exposure=0.0, look="Medium High Contrast"):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.view_settings.view_transform = "Filmic"
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
```

### 6.2 Setup Eevee (preview veloce)
```python
def setup_eevee(exposure=0.0):
    sc = bpy.context.scene
    try:    sc.render.engine = "BLENDER_EEVEE_NEXT"
    except: sc.render.engine = "BLENDER_EEVEE"
    sc.view_settings.view_transform = "Filmic"
    sc.view_settings.look = "Medium High Contrast"
    sc.view_settings.exposure = exposure
    # SSS e trasmission non funzionano bene in Eevee — usa Cycles per materiali organici
```

### 6.3 World (HDRI o colore piatto)
```python
def world_color(color=(0.03, 0.03, 0.04), strength=0.15):
    """Sfondo uniforme, neutro, scuro."""
    w = bpy.context.scene.world
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value    = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength

def world_hdri(hdri_path, strength=1.0, rotation_z=0.0):
    """HDRI world — illuminazione realistica da file .hdr o .exr."""
    w = bpy.context.scene.world
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    bg  = nt.nodes.new("ShaderNodeBackground");   bg.location  = (200, 0)
    env = nt.nodes.new("ShaderNodeTexEnvironment"); env.location = (-200, 0)
    tc  = nt.nodes.new("ShaderNodeTexCoord");       tc.location  = (-600, 0)
    mp  = nt.nodes.new("ShaderNodeMapping");        mp.location  = (-400, 0)
    out = nt.nodes.new("ShaderNodeOutputWorld");    out.location = (500, 0)

    env.image = bpy.data.images.load(hdri_path, check_existing=True)
    mp.inputs["Rotation"].default_value = (0.0, 0.0, rotation_z)

    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"],    env.inputs["Vector"])
    nt.links.new(env.outputs["Color"],    bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Strength"].default_value = strength
```

---

## Sezione 7 — Gotcha e compatibilità Blender 4.x / 5.x

| Problema | Blender 4.x | Blender 5.x | Soluzione |
|----------|------------|------------|-----------|
| Mix RGB deprecato | `ShaderNodeMixRGB` | rimosso | usa `ShaderNodeMix` con `data_type='RGBA'` |
| Mix RGBA inputs | `inputs[1]`, `inputs[2]` | `inputs[6]`, `inputs[7]` | usa sempre `[6]`/`[7]` per RGBA |
| Mix RGBA output | `outputs[0]` | `outputs[2]` | usa sempre `outputs[2]` |
| Mix Float inputs | `inputs[1]`, `inputs[2]` | `inputs[4]`, `inputs[5]` | usa `[4]`/`[5]` per FLOAT |
| Mix Float output | `outputs[0]` | `outputs[1]` | usa `outputs[1]` per FLOAT |
| SSS input name | `"Subsurface"` | `"Subsurface Weight"` | prova entrambi con `set_input()` |
| Clearcoat | `"Clearcoat"` | `"Coat Weight"` | prova entrambi |
| Specular | `"Specular"` | `"Specular IOR Level"` | prova entrambi |
| ColorRamp space | `color_space` | `color_mode` | try/except su entrambi |
| VertexColor node | `layer_name` | `attribute_name` | try/except su entrambi |
| Shade smooth | `bpy.ops.object.shade_smooth()` | lascia stripes su bmesh | usa `ob.data.shade_smooth()` direttamente |
| Eevee name | `"BLENDER_EEVEE"` | `"BLENDER_EEVEE_NEXT"` | try/except su entrambi |

### ShaderNodeMix — socket reference completo
```
data_type = 'RGBA':
  inputs[0]  = Factor
  inputs[6]  = A (Color)
  inputs[7]  = B (Color)
  outputs[2] = Result (Color)

data_type = 'FLOAT':
  inputs[0]  = Factor
  inputs[4]  = A (Float)
  inputs[5]  = B (Float)
  outputs[1] = Result (Float)

data_type = 'VECTOR':
  inputs[0]  = Factor
  inputs[8]  = A (Vector)
  inputs[9]  = B (Vector)
  outputs[3] = Result (Vector)
```

---

## Flusso di lavoro tipico

```
1. UV Unwrap        → smart_uv(obj_name) oppure unwrap_angle(obj_name)
2. Materiale        → scegli preset (mat_porcelain, mat_organic, mat_metal...)
                      oppure costruisci da zero con new_mat() + nodi
3. Assegna          → apply_mat(obj_name, mat)
4. Bake (opzionale) → bake_texture(obj_name, "AO") per ottimizzare il look
5. Render setup     → setup_cycles() oppure setup_eevee()
6. World            → world_color() o world_hdri(path)
```

---

## Esempio completo — Vasetto ceramica con materiale procedurale

```python
import bpy

# 1. UV Unwrap
smart_uv("Vase")

# 2. Materiale ceramica azzurra
mat, nodes, links = new_mat("CeramicBlue")
out  = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (200, 0)
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

noise = nodes.new("ShaderNodeTexNoise"); noise.location = (-400, 100)
noise.inputs["Scale"].default_value = 8.0
noise.inputs["Detail"].default_value = 3.0

mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.location = (-100, 100)
mix.inputs[6].default_value = (0.25, 0.45, 0.72, 1.0)  # blu scuro
mix.inputs[7].default_value = (0.35, 0.60, 0.88, 1.0)  # blu chiaro
links.new(noise.outputs["Fac"], mix.inputs[0])
links.new(mix.outputs[2], bsdf.inputs["Base Color"])

bsdf.inputs["Roughness"].default_value = 0.10
set_input(bsdf, "IOR", value=1.52)
set_input(bsdf, "Coat Weight", "Clearcoat", value=0.3)
set_input(bsdf, "Coat Roughness", "Clearcoat Roughness", value=0.04)

# 3. Assegna
apply_mat("Vase", mat)

# 4. Render Cycles
setup_cycles(samples=128, exposure=0.1)
world_color()
result = {"mat": mat.name, "applied": True}
```
