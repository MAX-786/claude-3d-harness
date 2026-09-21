# Skill: Blender Lighting & Camera

Sei un esperto di fotografia 3D e compositing in Blender. Il tuo ruolo è
configurare luci, camera, world e color management per ottenere render
professionali — con particolare attenzione a:
- oggetti chiari/bianchi che si sovraespongono facilmente
- contrasto soggetto/sfondo per product shots
- fedeltà cromatica per materiali organici, porcellana, metallo

---

## CONNESSIONE — MCP (predefinito)

```python
mcp__Blender__execute_blender_code(code="""
import bpy
# ... codice di setup luci/camera ...
result = {"ok": True}
""")
```

---

## DIAGNOSI RAPIDA — Problemi Comuni

| Sintomo | Causa | Fix |
|---------|-------|-----|
| Oggetto bianco "bruciato", nessun dettaglio | exposure troppo alto, look sbagliato | exposure -0.4/-0.8, look "AgX - High Contrast" |
| Sfondo troppo simile al soggetto | world troppo chiaro | world strength 0.05-0.15, color (0.02,0.02,0.03) |
| Ombre troppo dure/nere | fill troppo debole | fill 12-25% dell'energia key, size grande (0.8-1.5m) |
| Ombre troppo morbide/flat | fill troppo forte o size troppo grande | fill < 15% key, ridurre size fill |
| SSS / trasparenze spente | Eevee non le renderizza | Cycles obbligatorio per SSS/glass realistici |
| Riflessi troppo intensi | rim/key a energia eccessiva | dimezzare energy, aumentare size |
| Toni piatti, "CG look" | AgX/Filmic spento o look "None" | usare AgX + Punchy/High Contrast |
| Colori saturi che diventano grigi | Filmic "Notorious Six" | passare ad AgX (default da Blender 4.0+) |
| Area light non illumina nulla | rotazione con metodo matrix manuale | usare to_track_quat('-Z','Y') — UNICO metodo affidabile |
| Bordi alias / pixelati | samples bassi | EEVEE: samples 64+, Cycles: samples 256+ |

---

## COLOR MANAGEMENT — AgX Pipeline (default Blender 4.0+)

> **AgX ha sostituito Filmic come default da Blender 4.0.** Filmic è deprecato.
> Differenze chiave:
> - AgX: highlights → bianco naturale (come una camera reale)
> - Filmic: colori saturi collassano in 6 tonalità ("Notorious Six") — artefatto visibile
> - AgX: migliore shadow detail su oggetti scuri
> - AgX: supporta Display P3 e BT.1886 oltre sRGB
>
> **Per file esistenti che usano Filmic:** `scene.view_settings.view_transform = "AgX"`

```python
def setup_color_management(scene,
                            exposure=0.0,
                            look="AgX - Punchy",
                            view_transform="AgX"):
    """
    Configura AgX color management (standard da Blender 4.0+).

    exposure:
      0.0   → neutro (default per oggetti a toni medi)
     -0.4   → oggetti bianchi/chiari (porcellana, carta)
     +0.1   → oggetti molto scuri (plastica nera, pelle scura)
     +0.3   → scena sottoesposta da schiarire

    look AgX:
      "None"                 → flat/raw, solo per compositing esterno
      "AgX - Base"           → neutro, fedele ai colori, uso tecnico
      "AgX - Punchy"         → contrasto naturale, product shot standard  ← PREFERITO
      "AgX - High Contrast"  → drammatico, nero profondo, electronics/tech
      "AgX - Very High Contrast" → pubblicità, estremo

    look Filmic (legacy — evitare):
      "Medium High Contrast", "High Contrast" — per file vecchi pre-4.0

    REGOLA AgX:
      oggetti bianchi/chiari → exposure -0.4 + "AgX - Punchy"
      oggetti medi           → exposure 0.0  + "AgX - Punchy"
      oggetti scuri (TV, metallo) → exposure +0.1 + "AgX - High Contrast"
      organico/pelle         → exposure 0.0  + "AgX - Punchy"
    """
    scene.view_settings.view_transform = view_transform
    scene.view_settings.look           = look
    scene.view_settings.exposure       = exposure
    scene.view_settings.gamma          = 1.0

# Preset rapidi AgX:
def cm_product_white(scene):
    """Porcellana bianca, carta, tessuti chiari."""
    setup_color_management(scene, exposure=-0.4, look="AgX - Punchy")

def cm_product_neutral(scene):
    """Oggetti a colori medi, legno, plastica colorata."""
    setup_color_management(scene, exposure=0.0, look="AgX - Punchy")

def cm_product_dark(scene):
    """Metallo scuro, plastica nera, electronics (TV, smartphone)."""
    setup_color_management(scene, exposure=0.1, look="AgX - High Contrast")

def cm_organic(scene):
    """Frutta, pelle, materiali organici (SSS richiede Cycles)."""
    setup_color_management(scene, exposure=0.0, look="AgX - Punchy")

def cm_architectural(scene):
    """Interni/esterni, luce naturale."""
    setup_color_management(scene, exposure=0.0, look="AgX - Punchy")
```

---

## WORLD / BACKGROUND

```python
def setup_world(scene,
                color=(0.03, 0.03, 0.04),
                strength=0.15,
                hdri_path=None):
    """
    Configura il world background.

    PRODUCT SHOT (piccoli oggetti, sfondo scuro):
      color=(0.02,0.02,0.03), strength=0.10-0.20
      → quasi nero, soggetto risalta, ombre non troppo lunghe

    STUDIO NEUTRO:
      color=(0.05,0.05,0.06), strength=0.20
      → grigio scuro neutro, non distrae

    AMBIENTE CALDO:
      color=(0.04,0.03,0.02), strength=0.15
      → leggero tono ambra, buono per legno e pelle

    HDRI (Cycles only — environment realistico):
      hdri_path = "/path/to/hdri.hdr"
      strength = 0.5-2.0

    ATTENZIONE: world strength alto + oggetto bianco = overexposure
    Regola: se exposure < -0.3, tieni strength ≤ 0.20
    """
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    if hdri_path:
        # HDRI environment (Cycles)
        env   = nodes.new("ShaderNodeTexEnvironment")
        bg    = nodes.new("ShaderNodeBackground")
        out   = nodes.new("ShaderNodeOutputWorld")
        env.image = bpy.data.images.load(hdri_path)
        bg.inputs["Strength"].default_value = strength
        links.new(env.outputs["Color"], bg.inputs["Color"])
        links.new(bg.outputs["Background"], out.inputs["Surface"])
    else:
        # Colore solido
        bg  = nodes.new("ShaderNodeBackground")
        out = nodes.new("ShaderNodeOutputWorld")
        bg.inputs["Color"].default_value    = (*color, 1.0)
        bg.inputs["Strength"].default_value = strength
        links.new(bg.outputs["Background"], out.inputs["Surface"])

    return world


def setup_ground_plane(scene, collection,
                       color=(0.08, 0.05, 0.03),
                       roughness=0.55,
                       size=2.0,
                       z=0.0,
                       receive_shadow=True):
    """
    Piano del tavolo/pavimento per product shot.

    TAVOLO LEGNO SCURO (tazza espresso): color=(0.08,0.05,0.03) rough=0.55
    TAVOLO MARMO:   color=(0.85,0.82,0.78) rough=0.15  (Cycles SSR)
    TAVOLO METALLO: color=(0.20,0.20,0.22) rough=0.30 metallic=0.8
    CARTA BIANCA:   color=(0.92,0.92,0.90) rough=0.90
    SFONDO INFINITO (cyc): usare geometry shader o curve modifier
    """
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    plane = bpy.context.active_object
    plane.name = "Ground"

    mat = bpy.data.materials.new("Ground_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value  = roughness

    plane.data.materials.clear()
    plane.data.materials.append(mat)
    if collection:
        collection.objects.link(plane)
        bpy.context.scene.collection.objects.unlink(plane)
    return plane
```

---

## LUCI — Tre Punti Base

### Tipo di luce e dimensione — regole fondamentali

| Tipo | Ombre | Riflessi | Uso ideale |
|------|-------|----------|------------|
| AREA small (0.05–0.20m) | Dure, definite | Highlight puntuale | Rim, accent |
| AREA medium (0.25–0.50m) | Medie | Highlight pulito | Key product shot |
| AREA large (0.8–2.0m) | Morbide, diffuse | Ampia striscia | Fill, softbox |
| SUN | Parallele (no falloff) | — | Esterni, architettura |
| POINT | Omnidirezionali | — | Fill secondario, GI bounce |

**Ratio key/fill/rim consigliati:**

| Setup | Key | Fill | Rim | Risultato |
|-------|-----|------|-----|-----------|
| Product drammatico | 100% | 12–15% | 55–65% | Contrasto alto, tech/electronics |
| Product standard | 100% | 25–30% | 50% | Bilanciato, uso generale |
| Cibo/lifestyle | 100% | 33% | 40% | Morbido, luminoso |
| Ritratto | 100% | 50% | 30% | Viso, pelle |

```python
from mathutils import Vector
import bpy

def add_area(name, energy, location, target, size, color=(1,1,1), collection=None):
    """
    Crea AREA light orientata verso target con to_track_quat('-Z','Y').

    ✅ VERIFICATO Blender 5.x: to_track_quat('-Z','Y') funziona per AREA, SUN, SPOT.
    ❌ NON usare: rotazione via matrice manuale (causa Area light nera in Blender 5.x).

    size: dimensione lato (SQUARE) in BU
      0.05–0.20 → rim/accent (ombra dura)
      0.25–0.50 → key (ombra media)
      0.80–2.00 → fill/softbox (ombra morbida)
    """
    ld = bpy.data.lights.new(name=name, type='AREA')
    ld.energy = energy
    ld.color  = color
    ld.size   = size
    ld.shape  = 'SQUARE'
    lo = bpy.data.objects.new(name, ld)
    lo.location = location
    # Orienta la luce verso il target — UNICO metodo affidabile in Blender 5.x
    travel = (Vector(target) - Vector(location)).normalized()
    lo.rotation_euler = travel.to_track_quat('-Z', 'Y').to_euler()
    coll = collection or bpy.context.collection
    coll.objects.link(lo)
    return lo


def add_point(name, energy, location, color=(1,1,1), size=0.5, collection=None):
    """POINT light — omnidirezionale, nessuna rotazione necessaria."""
    ld = bpy.data.lights.new(name=name, type='POINT')
    ld.energy = energy
    ld.color  = color
    ld.shadow_soft_size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = location
    coll = collection or bpy.context.collection
    coll.objects.link(lo)
    return lo


def add_sun(name, energy, location, target, color=(1,1,1), collection=None):
    """SUN light orientato con to_track_quat — per esterni/architettura."""
    ld = bpy.data.lights.new(name=name, type='SUN')
    ld.energy = energy
    ld.color  = color
    lo = bpy.data.objects.new(name, ld)
    lo.location = location
    travel = (Vector(target) - Vector(location)).normalized()
    lo.rotation_euler = travel.to_track_quat('-Z', 'Y').to_euler()
    coll = collection or bpy.context.collection
    coll.objects.link(lo)
    return lo
```

---

## PRESET LUCI PER TIPO DI OGGETTO

### 1. Small Object — Product Shot (default)
Usare per: tazze, frutti, telefoni, gioielli, piccoli oggetti da tavolo (Ø < 30cm).

```python
def light_rig_small_object(obj_center=(0,0,0.04)):
    """
    Tre punti AREA per oggetto piccolo.
    Ratio: key=100%, fill=25%, rim=55%
    Color management: cm_product_neutral() — AgX Punchy
    """
    cx, cy, cz = obj_center
    t = (cx, cy, cz)  # target

    key  = add_area("Key",  energy=120, size=0.30,
                    location=(cx-0.30, cy-0.15, cz+0.36),
                    target=t, color=(1.00, 0.97, 0.90))

    fill = add_area("Fill", energy=30,  size=0.80,
                    location=(cx+0.32, cy+0.10, cz+0.18),
                    target=t, color=(0.85, 0.90, 1.00))

    rim  = add_area("Rim",  energy=65,  size=0.12,
                    location=(cx+0.00, cy+0.32, cz+0.28),
                    target=t, color=(1.00, 0.96, 0.88))

    return key, fill, rim


def light_rig_small_object_white(obj_center=(0,0,0.04)):
    """
    Variante per OGGETTI BIANCHI/CHIARI (porcellana, carta, ceramica).
    Key più grande → ombra morbida. Fill ridotto → forma visibile.
    Rim dimezzato → evita bordi bruciati su bianco.
    Color management: cm_product_white() — AgX Punchy, exposure -0.4
    """
    cx, cy, cz = obj_center
    t = (cx, cy, cz)

    key  = add_area("Key",  energy=100, size=0.45,
                    location=(cx-0.28, cy-0.14, cz+0.38),
                    target=t, color=(1.00, 0.97, 0.92))

    fill = add_area("Fill", energy=20,  size=1.00,
                    location=(cx+0.32, cy+0.12, cz+0.18),
                    target=t, color=(0.88, 0.93, 1.00))

    rim  = add_area("Rim",  energy=40,  size=0.12,
                    location=(cx+0.00, cy+0.30, cz+0.26),
                    target=t, color=(1.00, 0.97, 0.90))

    return key, fill, rim


def light_rig_dark_product(obj_center=(0,0,0.04)):
    """
    Per OGGETTI SCURI (TV, smartphone, plastica nera, metallo scuro).
    Fill molto ridotto (12%) → contrasto alto, evidenzia la forma.
    Rim potente → separa dal fondo scuro.
    Color management: cm_product_dark() — AgX High Contrast, exposure +0.1
    """
    cx, cy, cz = obj_center
    t = (cx, cy, cz)

    key  = add_area("Key",  energy=400, size=0.45,
                    location=(cx-1.2, cy-0.6, cz+1.1),
                    target=t, color=(1.00, 0.97, 0.92))

    fill = add_area("Fill", energy=50,  size=1.20,
                    location=(cx+1.2, cy-0.5, cz+0.3),
                    target=t, color=(0.88, 0.93, 1.00))

    rim  = add_area("Rim",  energy=250, size=0.15,
                    location=(cx+0.3, cy+2.0, cz+0.7),
                    target=t, color=(1.00, 0.96, 0.88))

    return key, fill, rim
```

### 2. Food & Organic — Macro/Close-up
Usare per: cibo, frutta, vegetali, oggetti con texture ricca.

```python
def light_rig_food(obj_center=(0,0,0.05)):
    """
    Setup morbido per cibo — key grande, fill generoso, backlight per traslucenza.
    Ratio: key=100%, fill=33%, back=58%
    NOTA: per SSS/traslucenza usare Cycles, non Eevee.
    Color management: cm_organic() — AgX Punchy
    """
    cx, cy, cz = obj_center
    t = (cx, cy, cz)

    key  = add_area("Key_Food",  energy=80,  size=0.80,
                    location=(cx-0.25, cy-0.20, cz+0.40),
                    target=t, color=(1.00, 0.98, 0.94))

    fill = add_area("Fill_Food", energy=26,  size=1.40,
                    location=(cx+0.40, cy+0.10, cz+0.10),
                    target=t, color=(0.90, 0.95, 1.00))

    back = add_area("Back_Food", energy=46,  size=0.50,
                    location=(cx+0.05, cy+0.40, cz+0.10),
                    target=t, color=(1.00, 0.95, 0.85))

    return key, fill, back
```

### 3. Furniture & Interior
Usare per: sedie, tavoli, lampade, oggetti di design (Ø 30cm–2m).

```python
def light_rig_furniture(scene, collection, obj_center=(0,0,0.5)):
    """
    Tre AREA per mobili/design. key=100%, fill=20%, rim=57%.
    Energie scale su scala 1:10 rispetto a small_object.

    Abbinare con: cm_product_neutral() → AgX Punchy, exposure=-0.1
    """
    cx, cy, cz = obj_center

    # KEY — sinistra e in alto, calda
    key = add_area("Key_Furn", energy=350, size=1.00,
        location=(cx-1.50, cy-0.80, cz+2.00),
        target=obj_center,
        color=(1.00, 0.97, 0.90),
        collection=collection)

    # FILL — destra, grande, fredda
    fill = add_area("Fill_Furn", energy=70, size=2.50,
        location=(cx+1.50, cy+0.50, cz+1.00),
        target=obj_center,
        color=(0.87, 0.92, 1.00),
        collection=collection)

    # RIM — dietro, stretto, contorno
    rim = add_area("Rim_Furn", energy=200, size=0.40,
        location=(cx+0.00, cy+2.00, cz+1.50),
        target=obj_center,
        color=(1.00, 0.96, 0.88),
        collection=collection)

    return key, fill, rim
```

### 4. Architectural — Exterior
Usare per: edifici, facciate, scene urbane.

```python
def light_rig_architectural(scene, collection,
                             sun_location=(5, -5, 8),
                             sun_target=(0, 0, 1.5)):
    """
    SUN (luce solare direzionale) + AREA sky fill.
    Cycles consigliato per GI corretta.

    Abbinare con: cm_architectural() → AgX Base, exposure=0.0
    """
    # Sole — SUN usa to_track_quat come gli AREA
    sun = add_sun("Sun",
        energy=4.5,
        location=sun_location,
        target=sun_target,
        color=(1.00, 0.96, 0.85),
        collection=collection)

    # Sky fill — AREA molto grande sopra la scena (simula cielo)
    fill = add_area("Sky_Fill",
        energy=800, size=8.0,
        location=(0, 0, 12),
        target=(0, 0, 0),
        color=(0.55, 0.75, 1.00),
        collection=collection)

    return sun, fill
```

---

## TECNICHE CINEMATOGRAFICHE — Named Lighting Patterns

> Queste tecniche vengono da fotografia, cinema e animazione professionale.
> Ogni tecnica ha un **posizionamento preciso**, un **ratio key:fill** e
> un **effetto emotivo** definito. Scegliere in base al contenuto narrativo,
> non solo all'estetica.

### Mappa ratio emotivi (Key:Fill)

| Ratio | Tipo scena | Effetto emotivo | Esempi |
|-------|-----------|-----------------|--------|
| 1:1   | High-key | Allegro, commedia, pubblicità fresca | Spot yogurt, cartoon |
| 2:1   | Lifestyle | Naturale, documentaristico | Food editorial, moda casual |
| 3:1   | Drammatico | Carattere, tensione lieve | Ritratto, product premium |
| 4:1   | Dark-dramatic | Misterioso, intrigante | Thriller, parfum, automotive |
| 8:1+  | Low-key / Noir | Angoscia, suspense, potere | Villain, horror, dark art |

**Regola pratica**: il ratio segue l'arco emotivo — scene di gioia salgono verso 1:1,
scene di conflitto scendono verso 8:1+.

### Temperatura colore (standard professionale)

| Luce | Temperatura | Uso |
|------|------------|-----|
| Key  | 3200–4000 K (warm amber) | Sorgente principale — dona calore naturale |
| Fill | 5500–6500 K (daylight) | Riempimento neutro — non contrasta col key |
| Rim  | 6500–8000 K (cool blue)  | Separazione dal fondo — effetto "halo" |

```python
# Conversione K → RGB lineare (approssimazione pratica)
TEMP_COLORS = {
    "tungsten":  (1.00, 0.70, 0.42),   # 3200K — very warm
    "warm":      (1.00, 0.82, 0.63),   # 4000K — warm
    "daylight":  (1.00, 0.97, 0.90),   # 5500K — neutral warm
    "neutral":   (1.00, 1.00, 1.00),   # 6500K — D65 neutral
    "cool":      (0.90, 0.95, 1.00),   # 7000K — slightly cool (fill)
    "sky":       (0.75, 0.87, 1.00),   # 9000K — cool blue (rim/sky)
}
# Uso professionale:
#   key_color  = TEMP_COLORS["warm"]     # (1.00, 0.82, 0.63)
#   fill_color = TEMP_COLORS["cool"]     # (0.90, 0.95, 1.00)
#   rim_color  = TEMP_COLORS["sky"]      # (0.75, 0.87, 1.00)
```

### Tecniche Named — Posizionamento e Setup

```python
def light_rig_loop(obj_center=(0,0,0.04), subject_height=0.08):
    """
    LOOP LIGHTING — tecnica standard ritratto/product.
    Key: 45° orizzontale dal soggetto, 30-45° in alto.
    Fill: lato opposto, 60-90° orizzontale, basso.
    Rim: 120-135° dal key, altezza media.

    Ratio key:fill = 2:1 → naturale, bilanciato.
    Loop = piccola ombra a forma di loop sotto il naso (ritratto),
           o ombra morbida laterale (oggetti).

    Usa per: product shot standard, ritratto lifestyle, cibo casual.
    """
    cx, cy, cz = obj_center
    h = subject_height
    t = (cx, cy, cz + h * 0.5)  # target = centro soggetto

    key  = add_area("Loop_Key",  energy=120, size=0.35,
                    location=(cx - h*3.5, cy - h*3.5, cz + h*3.5),  # 45° hor, 45° vert
                    target=t, color=(1.00, 0.82, 0.63))  # warm 4000K

    fill = add_area("Loop_Fill", energy=60,  size=1.00,
                    location=(cx + h*4.0, cy - h*1.0, cz + h*1.5),  # lato opposto
                    target=t, color=(0.90, 0.95, 1.00))  # cool fill

    rim  = add_area("Loop_Rim",  energy=65,  size=0.15,
                    location=(cx + h*1.0, cy + h*4.5, cz + h*2.5),  # dietro
                    target=t, color=(0.75, 0.87, 1.00))  # sky cool

    return key, fill, rim


def light_rig_rembrandt(obj_center=(0,0,0.04), subject_height=0.08):
    """
    REMBRANDT LIGHTING — drammatico, carattere forte.
    Key: 45° laterale, 45° in alto (come loop ma più laterale).
    Fill: molto debole o assente (ratio 3:1 → 4:1).
    Rim: stesso lato del fill, evidenzia profilo.

    Effetto: triangolo di luce illuminato sulla guancia in ombra (ritratto).
    Ratio key:fill = 3:1-4:1 → drammatico.

    Usa per: ritratto carattere, villain, product premium, noir leggero.
    """
    cx, cy, cz = obj_center
    h = subject_height
    t = (cx, cy, cz + h * 0.5)

    key  = add_area("Remb_Key",  energy=150, size=0.30,
                    location=(cx - h*4.5, cy - h*2.0, cz + h*4.0),  # più laterale
                    target=t, color=(1.00, 0.80, 0.58))  # tungsten warm

    fill = add_area("Remb_Fill", energy=40,  size=1.20,
                    location=(cx + h*3.0, cy - h*0.5, cz + h*0.8),  # molto debole
                    target=t, color=(0.90, 0.95, 1.00))

    rim  = add_area("Remb_Rim",  energy=80,  size=0.15,
                    location=(cx + h*2.0, cy + h*4.0, cz + h*2.0),
                    target=t, color=(0.75, 0.87, 1.00))

    return key, fill, rim


def light_rig_butterfly(obj_center=(0,0,0.04), subject_height=0.08):
    """
    BUTTERFLY / PARAMOUNT LIGHTING — glamour, bellezza.
    Key: direttamente davanti, in alto (non laterale).
    Fill: sotto il soggetto o assente.
    Rim: simmetrico, nessun lato dominante.

    Effetto: ombra a farfalla sotto il naso (ritratto).
    Ratio key:fill = 2:1-2.5:1 → luminoso, flattering.

    Usa per: beauty, gioielli, prodotti cosmetici, still life simmetrico.
    """
    cx, cy, cz = obj_center
    h = subject_height
    t = (cx, cy, cz + h * 0.5)

    key  = add_area("Btfly_Key",  energy=130, size=0.45,
                    location=(cx, cy - h*2.5, cz + h*4.5),  # frontale alto
                    target=t, color=(1.00, 0.97, 0.90))  # quasi neutro

    fill = add_area("Btfly_Fill", energy=52,  size=1.20,
                    location=(cx, cy - h*1.5, cz - h*0.5),  # sotto, luce di rimbalzo
                    target=t, color=(0.90, 0.95, 1.00))

    rim_l = add_area("Btfly_Rim_L", energy=55, size=0.15,
                     location=(cx - h*3.5, cy + h*3.0, cz + h*2.0),
                     target=t, color=(0.75, 0.87, 1.00))

    rim_r = add_area("Btfly_Rim_R", energy=55, size=0.15,
                     location=(cx + h*3.5, cy + h*3.0, cz + h*2.0),
                     target=t, color=(0.75, 0.87, 1.00))

    return key, fill, rim_l, rim_r


def light_rig_split(obj_center=(0,0,0.04), subject_height=0.08):
    """
    SPLIT LIGHTING — metà illuminata, metà in ombra.
    Key: 90° di lato (esattamente laterale), nessun fill.
    Rim: opposto al key, debole (o assente per effetto totale).

    Ratio key:fill = 8:1 o più → low-key, tensione massima.

    Usa per: dark product, villain, horror, automotive di notte, tech dark.
    """
    cx, cy, cz = obj_center
    h = subject_height
    t = (cx, cy, cz + h * 0.5)

    key = add_area("Split_Key", energy=200, size=0.20,
                   location=(cx - h*5.0, cy, cz + h*1.5),  # 90° laterale
                   target=t, color=(1.00, 0.80, 0.58))  # warm tungsten

    rim = add_area("Split_Rim", energy=25,  size=0.20,
                   location=(cx + h*4.5, cy + h*2.0, cz + h*1.5),
                   target=t, color=(0.70, 0.85, 1.00))  # cold blue

    return key, rim


def light_rig_high_key(obj_center=(0,0,0.04), subject_height=0.08):
    """
    HIGH-KEY LIGHTING — tutto luminoso, ombre quasi assenti.
    Ratio key:fill = 1:1 → allegro, pulito, commerciale.
    Molte sorgenti grandi da angoli diversi.

    Usa per: pubblicità alimentare, cosmetici, lifestyle positivo,
             cartoon, bambini, prodotti "fresh".
    """
    cx, cy, cz = obj_center
    h = subject_height
    t = (cx, cy, cz + h * 0.5)

    key   = add_area("HK_Key",   energy=90,  size=0.60,
                     location=(cx - h*3.0, cy - h*2.0, cz + h*4.0),
                     target=t, color=(1.00, 0.97, 0.90))

    fill  = add_area("HK_Fill",  energy=80,  size=1.20,
                     location=(cx + h*3.0, cy - h*1.5, cz + h*3.0),
                     target=t, color=(0.95, 0.97, 1.00))

    top   = add_area("HK_Top",   energy=60,  size=1.00,
                     location=(cx, cy - h*0.5, cz + h*6.0),  # overhead
                     target=t, color=(1.00, 1.00, 1.00))

    bounce= add_area("HK_Bounce",energy=40,  size=1.50,
                     location=(cx, cy - h*2.0, cz - h*0.5),  # sotto (bounce)
                     target=t, color=(0.95, 0.98, 1.00))

    return key, fill, top, bounce


def light_rig_low_key(obj_center=(0,0,0.04), subject_height=0.08):
    """
    LOW-KEY LIGHTING — scuro, drammatico, poca luce.
    Ratio key:fill = 8:1 → noir, mystery, tensione.
    Una sola sorgente principale, nessun fill.

    Usa per: horror, thriller, villain, whisky/spirits dark,
             automotive notturno, oggetti di lusso scuro.
    """
    cx, cy, cz = obj_center
    h = subject_height
    t = (cx, cy, cz + h * 0.5)

    key  = add_area("LK_Key",  energy=250, size=0.25,
                    location=(cx - h*3.5, cy - h*1.5, cz + h*4.0),
                    target=t, color=(1.00, 0.78, 0.48))  # molto warm/amber

    # Nessun fill → quasi tutto in ombra
    # Rim opzionale per separare dal fondo nero
    rim  = add_area("LK_Rim",  energy=30,  size=0.15,
                    location=(cx + h*3.0, cy + h*4.0, cz + h*2.0),
                    target=t, color=(0.60, 0.80, 1.00))  # cool blue contrasto

    return key, rim


def light_rig_food_side(obj_center=(0,0,0.05)):
    """
    FOOD SIDE LIGHTING — luce laterale per texture cibo.
    Key laterale 45° → rivela texture (granulosa, ruvida, fresca).
    Fill molto debole per non schiacciare le ombre di rilievo.
    Back light per separazione e traslucenza.

    Standard industria food photography (riviste, ristoranti premium).
    Usa con: Cycles (SSS), cm_organic(), piano legno o ardesia.
    """
    cx, cy, cz = obj_center

    key  = add_area("Food_SideKey", energy=70, size=0.60,
                    location=(cx - 0.30, cy + 0.00, cz + 0.25),  # laterale 90°
                    target=(cx, cy, cz), color=(1.00, 0.92, 0.80))  # warm 4500K

    fill = add_area("Food_Fill",    energy=12, size=1.40,
                    location=(cx + 0.35, cy - 0.20, cz + 0.15),
                    target=(cx, cy, cz), color=(0.90, 0.95, 1.00))

    back = add_area("Food_Back",    energy=45, size=0.40,
                    location=(cx + 0.05, cy + 0.45, cz + 0.20),  # dietro-laterale
                    target=(cx, cy, cz), color=(1.00, 0.95, 0.88))

    return key, fill, back


def light_rig_food_window(obj_center=(0,0,0.05)):
    """
    FOOD WINDOW LIGHT — simula finestra naturale laterale.
    Grande sorgente softbox = finestra diffusa.
    Ratio key:fill = 2:1 → morbido, lifestyle.
    """
    cx, cy, cz = obj_center

    window = add_area("Food_Window", energy=55, size=1.20,
                      location=(cx - 0.45, cy, cz + 0.30),  # finestra laterale
                      target=(cx, cy, cz), color=(1.00, 0.97, 0.90))

    bounce = add_area("Food_Bounce", energy=25, size=1.60,
                      location=(cx + 0.45, cy, cz + 0.05),  # riflettore bianco opposto
                      target=(cx, cy, cz), color=(0.95, 0.98, 1.00))

    return window, bounce
```

---

## HDRI — Illuminazione Ambiente Ibrida

> **Best practice moderna**: HDRI per global illumination + key light AREA per controllo artistico.
> HDRI da solo → realismo, ma niente controllo sulle ombre.
> HDRI + key → realismo con forma scultorea.
> Solo AREA → controllo totale, meno realismo.

```python
def setup_hdri_world(scene, hdri_path,
                     hdri_strength=0.6,
                     hdri_rotation_z=0.0,
                     add_solid_background=False,
                     bg_color=(0.03, 0.03, 0.04)):
    """
    Setup world HDRI — illuminazione ambiente realistica.
    Richiede Cycles per beneficio completo (GI vera).
    Eevee usa l'HDRI per probe/reflection ma non per GI vera.

    hdri_path:     percorso al file .hdr o .exr
    hdri_strength: 0.3-0.8 → ridotto (key AREA domina)
                   1.0-2.0 → pieno (HDRI è la luce principale)
    hdri_rotation_z: ruota HDRI per orientare le ombre (radianti)
    add_solid_background: True → sfondo colore solido + HDRI solo per illuminazione

    WORKFLOW IBRIDO CONSIGLIATO:
      1. setup_hdri_world(sc, path, strength=0.5)  → GI e rimbalzi
      2. add_area("Key", energy=80, ...)            → controllo forma
      ↓ HDRI fornisce rimbalzi di luce naturali
      ↓ Key AREA fornisce direzione, ombre scultoree
    """
    import math

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world
    world.use_nodes = True
    tree  = world.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # Texture coordinate per rotazione
    tc  = nodes.new("ShaderNodeTexCoord")
    map = nodes.new("ShaderNodeMapping")
    map.inputs["Rotation"].default_value = (0, 0, hdri_rotation_z)

    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(hdri_path)

    if add_solid_background:
        # HDRI per illuminazione, colore solido per sfondo
        # (Cycles — Light Path node)
        lp  = nodes.new("ShaderNodeLightPath")
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = 'MIX'
        bg_node = nodes.new("ShaderNodeBackground")
        bg_node.inputs["Color"].default_value = (*bg_color, 1.0)

        hdri_bg = nodes.new("ShaderNodeBackground")
        hdri_bg.inputs["Strength"].default_value = hdri_strength

        mix_bg = nodes.new("ShaderNodeMixShader")
        out    = nodes.new("ShaderNodeOutputWorld")

        links.new(tc.outputs["Generated"], map.inputs["Vector"])
        links.new(map.outputs["Vector"],   env.inputs["Vector"])
        links.new(env.outputs["Color"],    hdri_bg.inputs["Color"])
        links.new(lp.outputs["Is Camera Ray"], mix_bg.inputs["Fac"])
        links.new(bg_node.outputs["Background"],  mix_bg.inputs[1])
        links.new(hdri_bg.outputs["Background"],  mix_bg.inputs[2])
        links.new(mix_bg.outputs["Shader"],        out.inputs["Surface"])
    else:
        # HDRI puro per background e illuminazione
        bg  = nodes.new("ShaderNodeBackground")
        bg.inputs["Strength"].default_value = hdri_strength
        out = nodes.new("ShaderNodeOutputWorld")

        links.new(tc.outputs["Generated"], map.inputs["Vector"])
        links.new(map.outputs["Vector"],   env.inputs["Vector"])
        links.new(env.outputs["Color"],    bg.inputs["Color"])
        links.new(bg.outputs["Background"], out.inputs["Surface"])

    return world


# Preset HDRI per scena — strength ridotta (key AREA domina)
HDRI_PRESETS = {
    "studio_neutral":    {"strength": 0.40, "notes": "Studio neutro, niente rimbalzi esterni"},
    "overcast_sky":      {"strength": 0.60, "notes": "Luce diffusa naturale, ombre morbide"},
    "golden_hour":       {"strength": 0.50, "notes": "Warm sunset, colore ambra"},
    "night_city":        {"strength": 0.30, "notes": "Scena notturna urbana, rimbalzi colorati"},
    "hdri_only_no_key":  {"strength": 1.20, "notes": "HDRI unica sorgente, realistico puro"},
}
```

---

## CAMERA

```python
def setup_camera(scene, collection,
                 location=(0.26, -0.32, 0.16),
                 target=(0, 0, 0.04),
                 lens=85,
                 dof_distance=None,
                 dof_fstop=2.8,
                 clip_start=0.001,
                 clip_end=100.0):
    """
    Configura la camera e la punta verso il target.

    FOCALI CONSIGLIATE:
      35mm  → architettura, ambienti, campo lungo
      50mm  → uso generale, "occhio umano"
      85mm  → product shot piccoli oggetti (tazze, gioielli) — PREFERITA
      135mm → ritratto, dettaglio, comprimi la profondità
      200mm → macro simulato, molto compresso

    DOF (Depth of Field):
      dof_distance: distanza dal piano a fuoco in BU (None = disabilitato)
      dof_fstop:   apertura diaframma — più basso = più sfocatura
        1.4  → molto sfocato (macro artistico)
        2.8  → sfocatura moderata (product standard)
        5.6  → leggera sfocatura
        11.0 → tutto a fuoco

    POSIZIONE CAMERA — regole pratiche:
      Angolo 3/4 classico: elevation ~35°, azimuth ~40°
      Top-down: elevation 70-85° (food, gioielli su superficie)
      Eye level: elevation 5-15° (architettura, auto)
      Leggermente sotto: elevation -5° (edificio → aspetto maestoso)
    """
    from mathutils import Vector

    # Crea o recupera camera
    if "Camera" in bpy.data.cameras:
        cam_data = bpy.data.cameras["Camera"]
    else:
        cam_data = bpy.data.cameras.new("Camera")

    cam_data.lens       = lens
    cam_data.clip_start = clip_start
    cam_data.clip_end   = clip_end

    # DOF
    if dof_distance is not None:
        cam_data.dof.use_dof          = True
        cam_data.dof.focus_distance   = dof_distance
        cam_data.dof.aperture_fstop   = dof_fstop
    else:
        cam_data.dof.use_dof = False

    # Crea o recupera oggetto camera
    if "Camera" in bpy.data.objects:
        cam_obj = bpy.data.objects["Camera"]
        cam_obj.data = cam_data
    else:
        cam_obj = bpy.data.objects.new("Camera", cam_data)
        collection.objects.link(cam_obj)

    cam_obj.location = location
    scene.camera = cam_obj

    # Punta la camera verso il target
    direction = (Vector(target) - Vector(location)).normalized()
    up = Vector((0, 0, 1))
    if abs(direction.dot(up)) > 0.99:
        up = Vector((1, 0, 0))
    right = direction.cross(up).normalized()
    up    = right.cross(direction).normalized()
    from mathutils import Matrix
    R = Matrix((right, up, -direction)).transposed()
    cam_obj.rotation_euler = R.to_euler()

    return cam_obj


def camera_from_object_size(obj_width_bu, obj_height_bu,
                             elevation_deg=35, azimuth_deg=40,
                             lens=85, margin=1.3):
    """
    Calcola posizione camera ottimale per inquadrare l'oggetto.
    Ritorna dict con location, target, lens.

    obj_width_bu, obj_height_bu: dimensioni dell'oggetto in Blender Units
    elevation_deg: angolo di elevazione dalla orizzontale
    azimuth_deg:   angolo orizzontale dall'asse Y
    margin:        fattore di margine (1.3 = 30% extra)
    """
    import math
    # FOV verticale per focale 85mm su sensore 36mm full frame
    # fov_v = 2*atan(18/f) in radianti
    fov_half_v = math.atan(18.0 / lens)
    diag = math.sqrt(obj_width_bu**2 + obj_height_bu**2)
    dist = (diag / 2) / math.tan(fov_half_v) * margin

    el = math.radians(elevation_deg)
    az = math.radians(azimuth_deg)
    x = dist * math.cos(el) * math.sin(az)
    y = -dist * math.cos(el) * math.cos(az)
    z = dist * math.sin(el) + obj_height_bu / 2

    return {
        "location": (x, y, z),
        "target":   (0, 0, obj_height_bu / 2),
        "lens":     lens,
    }
```

---

## RENDER ENGINE & SETTINGS

```python
def setup_render(scene,
                 engine="EEVEE",
                 resolution=(1280, 720),
                 samples=64,
                 output_path=None,
                 use_compositing=False):
    """
    Configura render engine e output.

    EEVEE (predefinito):
      Pro: veloce, anteprima in tempo reale
      Contro: no SSS vero, no caustiche, riflessi approssimati
      Samples: 32-64 per preview, 128+ per produzione

    CYCLES:
      Pro: SSS fisicamente corretto, vetro, caustiche, GI vera
      Contro: lento (anche 10-60 min per frame)
      Samples: 128 per preview, 512-1024 per produzione
      Usare SEMPRE per: porcellana con SSS, frutta, pelle, vetro

    ATTENZIONE Eevee: per vedere SSS in Eevee, abilitare
      scene.eevee.use_gtao = True  (AO)
      scene.eevee.use_ssr  = True  (screen-space reflections)
    """
    sc = scene

    # Engine
    if engine.upper() in ("EEVEE", "EEVEE_NEXT"):
        try:
            sc.render.engine = "BLENDER_EEVEE_NEXT"
        except:
            sc.render.engine = "BLENDER_EEVEE"
        # Opzioni Eevee
        try:
            sc.eevee.taa_render_samples     = samples
            sc.eevee.use_gtao               = True
            sc.eevee.use_ssr                = True
            sc.eevee.ssr_quality            = 0.5
        except AttributeError:
            pass
    elif engine.upper() == "CYCLES":
        sc.render.engine = "CYCLES"
        sc.cycles.samples          = samples
        sc.cycles.use_denoising    = True
        try:
            sc.cycles.denoiser = "OPTIX"   # GPU NVIDIA
        except:
            sc.cycles.denoiser = "OPENIMAGEDENOISE"

    # Risoluzione
    sc.render.resolution_x = resolution[0]
    sc.render.resolution_y = resolution[1]
    sc.render.resolution_percentage = 100
    sc.render.use_compositing = use_compositing

    # Output
    if output_path:
        sc.render.filepath     = output_path
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode  = "RGBA"

    return sc


# Preset rapidi:
def render_preview(scene, output_path):
    """Anteprima veloce EEVEE 720p 32 samples."""
    setup_render(scene, "EEVEE", (1280, 720), samples=32,
                 output_path=output_path)
    setup_color_management(scene, exposure=-0.2, look="Medium High Contrast")

def render_product(scene, output_path, white_subject=False):
    """Product shot EEVEE 1080p 128 samples."""
    setup_render(scene, "EEVEE", (1920, 1080), samples=128,
                 output_path=output_path)
    if white_subject:
        cm_product_white(scene)
    else:
        cm_product_neutral(scene)

def render_quality(scene, output_path, white_subject=False):
    """Alta qualità Cycles 1080p 512 samples (SSS, vetro, pelle)."""
    setup_render(scene, "CYCLES", (1920, 1080), samples=512,
                 output_path=output_path)
    if white_subject:
        cm_product_white(scene)
    else:
        cm_organic(scene)
```

---

## SETUP COMPLETO — Template Funzione Principale

```python
def setup_full_scene(scene_name="ProductShot",
                     subject_obj=None,
                     subject_type="small_white",
                     output_path=None):
    """
    Setup completo in una chiamata.

    subject_type:
      "small_white"   → porcellana, ceramica, carta (tazza, piatto)
      "small_colored" → oggetti a colori medi
      "small_dark"    → metallo scuro, pelle nera
      "food"          → cibo, frutta (richiede Cycles per SSS)
      "furniture"     → oggetti medi (sedie, lampade)
      "architectural" → edifici, scene esterne
    """
    import bpy, math
    sc = bpy.context.scene

    # Collection luci
    if "Lights" in bpy.data.collections:
        lights_col = bpy.data.collections["Lights"]
    else:
        lights_col = bpy.data.collections.new("Lights")
        sc.collection.children.link(lights_col)

    # Centro oggetto (usa bounding box se disponibile)
    if subject_obj:
        bpy.context.view_layer.update()
        verts = [subject_obj.matrix_world @ v.co
                 for v in subject_obj.data.vertices]
        from mathutils import Vector
        mn = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
        mx = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
        center = tuple((mn + mx) / 2)
        obj_w  = (mx - mn).x
        obj_h  = (mx - mn).z
    else:
        center = (0, 0, 0.04)
        obj_w, obj_h = 0.1, 0.08

    # Scegli preset luci
    if subject_type in ("small_white",):
        light_rig_small_object_white(sc, lights_col, center)
        cm_product_white(sc)
        engine, samples = "EEVEE", 128
    elif subject_type == "food":
        light_rig_food(sc, lights_col, center)
        cm_organic(sc)
        engine, samples = "CYCLES", 512
    elif subject_type == "furniture":
        light_rig_furniture(sc, lights_col, center)
        cm_product_neutral(sc)
        engine, samples = "EEVEE", 128
    elif subject_type == "architectural":
        light_rig_architectural(sc, lights_col)
        cm_architectural(sc)
        engine, samples = "CYCLES", 256
    else:  # small_colored, small_dark, default
        light_rig_small_object(sc, lights_col, center)
        cm_product_neutral(sc)
        engine, samples = "EEVEE", 128

    # Camera automatica
    cam_spec = camera_from_object_size(obj_w, obj_h)
    setup_camera(sc, lights_col,
                 location=cam_spec["location"],
                 target=cam_spec["target"],
                 lens=cam_spec["lens"])

    # World scuro
    setup_world(sc, color=(0.02, 0.02, 0.03), strength=0.12)

    # Ground plane
    setup_ground_plane(sc, sc.collection,
                       color=(0.08, 0.05, 0.03), roughness=0.55,
                       size=max(obj_w * 8, 1.0))

    # Render
    if output_path:
        setup_render(sc, engine, (1920, 1080), samples=samples,
                     output_path=output_path)

    return sc
```

---

## CHEAT SHEET RAPIDO

```
PROBLEMA: oggetto bianco sovraesposto
FIX:      exposure=-0.4, look="AgX - Punchy"
          key size=0.45 (più morbido), rim energy dimezzato
          world strength ≤ 0.15

PROBLEMA: sfondo non contrasta col soggetto chiaro
FIX:      world color=(0.02,0.02,0.03), strength=0.10
          ground_plane color=(0.06,0.04,0.02)

PROBLEMA: ombre nere/piatte
FIX:      fill energy = 20-25% di key
          fill size = 2× key size

PROBLEMA: bordi oggetto non si staccano dallo sfondo
FIX:      rim light dietro il soggetto, energy = 40-60% key
          rim color cool (0.75, 0.87, 1.00) — sky blue

PROBLEMA: SSS / vetro non realistico in Eevee
FIX:      cambiare engine a Cycles

PROBLEMA: render troppo "CG" / piatto
FIX:      AgX "Punchy" o "High Contrast" — mai usare "None" o "Standard"
          Non usare Filmic su Blender 4.0+ (colori saturi → Notorious Six)

PROBLEMA: troppo lento (Cycles)
FIX:      Usa GPU (OPTIX per NVIDIA), denoiser OPTIX
          Samples 128 per anteprima, 512 per finale
          Firefly filter: cycles.use_light_tree = True

PROBLEMA: scegliere tecnica di illuminazione
GUIDA:
  Product/still life neutr  → loop (2:1)
  Product premium/ritratto  → rembrandt (3:1-4:1)
  Beauty/gioielli           → butterfly (2:1-2.5:1)
  Dark product/thriller     → split o low_key (8:1+)
  Cibo editoriale           → food_side + back light
  Cibo lifestyle/finestra   → food_window (2:1)
  Allegro/pubblicità        → high_key (1:1)
  HDRI realismo + controllo → setup_hdri_world() + key AREA

TEMPERATURA COLORE:
  key=warm (1.00, 0.82, 0.63) — 4000K
  fill=cool (0.90, 0.95, 1.00) — standard
  rim=sky (0.75, 0.87, 1.00) — 9000K
  → contrasto caldo/freddo = look professionale
```
