---
description: >
  Coordinator per la pipeline di modellazione 3D in Blender. Riceve la richiesta
  dell'utente, decide se serve ricerca (blender-research), analizza lo spec_sheet,
  sceglie la tecnica di modellazione per ogni parte, pianifica le dipendenze e
  l'ordine di costruzione, poi orchestra blender-arch, blender-procedural,
  blender-rig, blender-sculpt, blender-geonodes, blender-texture, blender-lighting e blender-physics
  secondo il tipo di geometria e le esigenze di render.
  Pipeline completa: research → coordinator → arch / procedural / rig / sculpt / geonodes / texture / lighting / physics.
  Trigger: qualsiasi richiesta di creazione di oggetti 3D ("voglio creare X") o di setup render/luce/camera.
allowed-tools:
  - Bash
  - Read
  - Write
  - WebSearch
  - mcp__Blender__execute_blender_code
  - mcp__Blender__get_objects_summary
  - mcp__Blender__get_screenshot_of_window_as_image
  - mcp__Blender__render_viewport_to_path
---

# Skill: Blender Coordinator

Sei l'architetto della pipeline di modellazione 3D. Il tuo ruolo è trasformare
una richiesta (vaga o dettagliata) in un **build_plan** eseguibile, coordinando
la ricerca e la modellazione senza sovrapporre le responsabilità.

---

## PIPELINE COMPLETA

```
UTENTE: "voglio creare X"
        │
        ▼
[COORDINATOR — questa skill]
        │
        ├─► STEP 0: valuta la richiesta
        │     Vaga? → chiama blender-research
        │     Dettagliata? → costruisci spec_sheet manuale
        │
        ├─► STEP 1: analizza spec_sheet
        │     Quante parti? Dipendenze? Complessità?
        │
        ├─► STEP 2: scegli SKILL + tecnica per ogni parte
        │     (vedi tabella ROUTING SKILL)
        │
        ├─► STEP 3: pianifica dipendenze e ordine
        │     Chi dipende da chi? Cosa va fatto prima?
        │
        ├─► STEP 4: pianifica materiali e scena
        │     Materiali condivisi? Luci appropriate?
        │
        ├─► STEP 5: produci build_plan
        │
        └─► STEP 5b: GATE DI PIANO (plan_validator) — OBBLIGATORIO
              plan_validator.validate(Plan) deve PASSARE
              → solo allora passa alla skill per l'esecuzione
```

---

## ROUTING SKILL — Quale skill usare?

| Tipo di geometria / richiesta | Skill da invocare |
|-------------------------------|-------------------|
| Oggetti rigidi, architettura, mobili, prodotti | **blender-arch** |
| Oggetto manifatturiero **panelizzato + cuciture** (scarpa, stivale, borsa, imbottito, scocca, guanto) | **blender-arch** → `assembly_kernel` |
| Strutture biologiche (cuore, vasi, DNA) | **blender-procedural** |
| Tubi, cavi, pipe lungo una curva 3D | **blender-procedural** |
| Eliche, strutture ripetitive su spine | **blender-procedural** |
| Loft da profili variabili (colonna, vaso anatomico) | **blender-procedural** |
| Crescita differenziale, superfici organiche | **blender-procedural** |
| Scheletro / armatura / rig | **blender-rig** |
| Deformazioni biomeccaniche (nocca, muscolo) | **blender-rig** |
| Pelle su scheletro, weight painting | **blender-rig** |
| FK/IK, animazione articolata | **blender-rig** |
| Forma organica/irregolare (frutta, roccia, terreno) | **blender-sculpt** |
| Dettagli superficie (rughe, pori, bump, dents) | **blender-sculpt** |
| Displacement noise su mesh | **blender-sculpt** |
| Morphing / Shape Key da sculpt | **blender-sculpt** |
| Posizionamento preciso, attach point | **blender-space** |
| Materiali, UV unwrap, baking, PBR texture | **blender-texture** |
| SSS, Fresnel, materiali organici/ceramica/legno | **blender-texture** |
| Bake AO / Normal Map su immagine | **blender-texture** |
| Scatter su superficie, istanziazione non-distruttiva | **blender-geonodes** |
| Curve-to-mesh, pipe via modifier | **blender-geonodes** |
| Displacement / noise via Geometry Nodes | **blender-geonodes** |
| Setup luci, camera, render per product shot | **blender-lighting** |
| Oggetti bianchi/chiari sovraesposti nel render | **blender-lighting** |
| AgX/Filmic look, color management, exposure | **blender-lighting** |
| World/background, contrasto soggetto/sfondo | **blender-lighting** |
| Oggetto che cade / rimbalza senza deformarsi | **blender-physics** (Rigid Body) |
| Oggetto morbido che si schiaccia / deforma | **blender-physics** (Soft Body) |
| Pallone / oggetto gonfiabile con deformazione | **blender-physics** (Cloth + Pressure) |
| Tessuto / vestito / bandiera / tenda | **blender-physics** (Cloth) |
| Vento / turbolenza su Cloth o Soft Body | **blender-physics** (Force Field) |
| Pioggia / polvere / particelle / fumo | **blender-physics** (Particles) |
| Oggetto complesso = parti miste | **più skill in sequenza** |

### Regola di composizione (parti miste):
```
Esempio: "mano animata che tiene un oggetto"
  ├─ geometria mano (skin) → blender-procedural (Generalized Cylinder)
  ├─ scheletro + deformazioni → blender-rig
  └─ oggetto tenuto (spada) → blender-arch (product modeling)
         │
         └─► Socket System (CHILD_OF) → blender-rig
```

---

## STEP 0 — VALUTA LA RICHIESTA

### Criteri per chiamare blender-research:

| Condizione | Azione |
|-----------|--------|
| Richiesta vaga (solo nome oggetto) | → chiama blender-research |
| Mancano dimensioni | → chiama blender-research |
| Mancano colori/materiali | → chiama blender-research |
| Oggetto con parti multiple non descritte | → chiama blender-research |
| Richiesta dettagliata con misure esplicite | → costruisci spec_sheet diretto |
| Oggetto semplice (sfera, cubo, piano) | → vai diretto a blender-arch |

### Livelli di complessità:

```
SEMPLICE  (1 parte, forma primitiva)      → diretto a blender-arch
MEDIO     (2-4 parti, forme standard)     → research + coordinator + arch
COMPLESSO (5+ parti, forme organiche)     → research + coordinator + arch iterativo
```

---

## STEP 1 — ANALISI SPEC_SHEET

Dopo aver ricevuto lo spec_sheet da blender-research (o averlo costruito):

```python
def analizza_spec(spec_sheet):
    """
    Esamina lo spec_sheet e produce una mappa di complessità per parte.
    """
    analysis = {}
    for part_name, part in spec_sheet["parts"].items():
        analysis[part_name] = {
            "shape_family":  classifica_forma(part["shape"]),
            "complexity":    stima_complessita(part),
            "technique":     scegli_tecnica(part),
            "dependencies":  spec_sheet["dependencies"].get(part_name, None),
            "blender_units": converti_blender_units(part),
        }
    return analysis

def classifica_forma(shape_str):
    """Mappa la descrizione testuale a una famiglia geometrica."""
    shape_str = shape_str.lower()
    if any(k in shape_str for k in ["sphere","ball","round","glob"]):
        return "sphere"
    if any(k in shape_str for k in ["cylinder","tube","pipe","rod"]):
        return "cylinder"
    if any(k in shape_str for k in ["cone","taper","truncat"]):
        return "cone"
    if any(k in shape_str for k in ["disc","disk","flat","plate","saucer"]):
        return "disc"
    if any(k in shape_str for k in ["box","cube","rect","block"]):
        return "box"
    if any(k in shape_str for k in ["arc","loop","curve","bend","hook"]):
        return "curve"
    if any(k in shape_str for k in ["organic","irregular","freeform","sculpt"]):
        return "organic"
    if any(k in shape_str for k in ["lathe","revolv","revolution","vase"]):
        return "lathe"
    return "unknown"
```

---

## STEP 2 — METHOD SELECTION FRAMEWORK

Prima di scegliere la tecnica, esegui questo decision tree per ogni parte:

```
Parte da modellare
        │
        ▼
Ha una SPINE (asse principale lungo cui scorre la geometria)?
        │
       SÌ ──────────────────────────────────────────► NO
        │                                              │
La sezione cambia                          Ha forma definita e
significativamente lungo la spine?          parametrizzabile?
   SÌ          NO                           SÌ          NO
    │           │                            │           │
build_shell  build_vessel              arch / lathe    sculpt
(profili     (sezione                  (box/cyl/disc/  (UV sphere
 variabili)   costante)                 revolution)     + brush)
                │
    Ha influenze globali (gravità, attrattori, rumore)?
        SÌ  → vector_blend + tropismo / noise (Sez. 10)
        NO, ha waypoint + cambi direzione discreti?
        SÌ  → state_machine + fillet (Sez. 11)
    Ha biforcazioni / topologia complessa?
        SÌ  → grafo + cinematica ibrida (Sez. 12-13)
```

### Tabella diagnostica rapida

| Segnale diagnostico | Tecnica primaria | Skill |
|--------------------|-----------------|-------|
| Simmetria di rivoluzione (tazza, vaso) | LATHE / bmesh rings | arch |
| Sezione costante su percorso (tubo, cavo) | build_vessel | procedural |
| Sezione variabile su percorso (cuore, osso) | build_shell | procedural |
| Spine + influenza globale (vite rampicante) | vector_blend_step | procedural |
| Spine + waypoint discreti (bambù, tubatura) | state_machine + fillet | procedural |
| Biforcazioni / albero vascolare | grafo (MST) + build_vessel | procedural |
| Box/cylinder/cone con modificatori | CUBE/CYL + bevel/boolean | arch |
| Oggetto fatto di **pannelli cuciti** (calzatura, borsa, imbottito, scocca) | `assembly_kernel`: pannelli su master/last + **SeamCurve/JunctionPoint condivisi** | arch |
| Forma libera senza asse (frutta, roccia) | UV_SPHERE + sculpt | sculpt |
| Ripetizione su superficie | scatter / array | geonodes |
| Deformazione animata | armature + skin | rig |

### Priorità in caso di ambiguità

```
1. Spine presente?         → procedural batte arch
2. Animazione richiesta?   → rig batte tutto il resto
3. Forma organica pura?    → sculpt batte arch
4. Scatter/ripetizione?    → geonodes batte arch (array)
5. PANELIZZATO + cuciture? → arch via assembly_kernel  [GATED, vedi sotto]
6. Default (forma rigida)  → arch
```

> **Gate regola 5 — quando (e SOLO quando) usare `assembly_kernel`:**
> l'oggetto è *costruito da pannelli piatti/curvi uniti da cuciture*
> (calzature, borse, imbottiti, scocche, guanti). NON è una forma organica
> a superficie unica (→ sculpt/procedural) né una primitiva con modificatori
> (→ arch normale) né un tubo a spine (→ procedural). Se panelizzato+cuciture:
> blender-arch DEVE usare il paradigma `assembly_kernel` (pannelli su un
> master/last + `SeamCurve`/`JunctionPoint` **condivisi**), **MAI** un loft
> o boolean singolo "tutto in uno" — è la causa-radice del fallimento
> "calzino" (vedi sezione dedicata in blender-arch).

---

## STEP 2b — FALLBACK CHAINS

Quando il metodo primario produce artefatti, segui questa catena prima di ricominciare da zero:

```python
FALLBACK_CHAINS = {

    "LATHE / bmesh_rings": [
        # Artefatto               Fix
        ("topologia sporca ai poli",  "aggiungi ring intermedio vicino all'apice"),
        ("shade stripes su cilindro", "usa obj.data.shade_smooth() NON ops.shade_smooth"),
        ("boolean fallisce",          "subdivide PRIMA del boolean, solver='EXACT'"),
        ("pareti troppo sottili",     "aumenta segments o aggiungi loop_cuts manuali"),
        # Fallback totale: LATHE → build_shell (più controllo sui profili)
    ],

    "build_vessel": [
        ("frame flippa 180°",         "reortho(T, N) ogni 10-20 passi"),
        ("mesh non chiusa alle capi", "aggiungi cap: bm.faces.new(ring_end)"),
        ("sezione deformata",         "riduci step_distance o aumenta segments"),
        ("self-intersection su curva stretta", "riduci radius o aumenta n_steps"),
        # Fallback totale: build_vessel → geonodes curve-to-mesh (più flessibile sui cap)
    ],

    "build_shell": [
        ("profili non allineati tra ring",  "verifica ordine CCW di tutti i ring"),
        ("facce invertite",                 "bm.normal_update() dopo ogni loft_rings"),
        ("transizione brusca tra sezioni",  "interpola frame intermedi con lerp"),
        # Fallback totale: build_shell → sculpt su UV_SPHERE (se forma troppo complessa)
    ],

    "sculpt": [
        ("troppo coarse",        "remesh voxel 0.003-0.005 prima di sculptare"),
        ("normali invertite",    "Recalculate Outside in Edit Mode"),
        ("no UV per texture",    "smart_uv_project() dopo sculpt"),
        # Fallback totale: sculpt → procedural con più rings (se serve parametrizzabilità)
    ],

    "state_machine + fillet": [
        ("spigolo vivo al cambio",    "aumenta fillet_steps (1 → 8)"),
        ("self-intersection al raccordo", "riduci step_size × fillet_steps"),
        ("direzioni non allineate",   "usa rotation_difference() non angoli Euler"),
        # Fallback totale: state_machine → vector_blend (se i cambi sono fluidi non discreti)
    ],

    "boolean": [
        ("mesh non manifold dopo cut",  "valida con obj.data.validate(), usa EXACT"),
        ("SubSurf dopo boolean → artefatti", "SubSurf PRIMA del boolean, poi applicalo"),
        ("cutter troppo piccolo",       "scala cutter 1.01x sull'asse di taglio"),
        # Fallback totale: boolean → displacement/sculpt (per dettagli non critici)
    ],
}
```

### Regola generale di fallback

```
Se il metodo A fallisce dopo 2 tentativi di fix:
  1. Valuta se il problema è geometrico (topologia) → passa a metodo B più controllato
  2. Valuta se il problema è di scala → verifica UNIT = 0.1, converti tutto in BU
  3. Valuta se il problema è di ordine (SubSurf/Boolean) → riparti dall'ordine corretto
  4. Solo dopo: passa alla tecnica alternativa

Mai: eliminare la mesh e rifare senza diagnosticare l'artefatto.
```

---

## STEP 2c — TECNICHE DI MODELLAZIONE

Per ogni parte, scegli la tecnica più appropriata:

| Famiglia | Tecnica consigliata | Quando usarla |
|----------|--------------------|----|
| `sphere` | `UV_SPHERE` + sculpt | Frutta, teste, oggetti rotondi |
| `cylinder` | `CYLINDER` + bevel | Tazze, barattoli, colonne |
| `cone` | `CONE` o bmesh rings | Imbuti, coni, beakers |
| `disc` | `CIRCLE` + fill + extrude | Piatti, coperchi, monete |
| `box` | `CUBE` + loop cuts | Mobili, scatole, edifici |
| `curve` | Bezier/NURBS + bevel | Manici, fili, tubi curvi |
| `organic` | UV_SPHERE + sculpt_brush | Frutti, rocce, forme libere |
| `lathe` | bmesh profile rings | Vasi, bottiglie, oggetti di rivoluzione |
| `flat_sheet` | `PLANE` + subdivide | Foglie, tessuti, piani |

### Pattern di codice per ogni tecnica:

```python
# ── UV_SPHERE (frutta, palloni) ──────────────────────────────────
"""
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=r,          # dal spec_sheet: width_cm/2 * 0.01
    segments=64,       # più segmenti = più definizione
    ring_count=48,
    location=(0,0,0)
)
# Poi: origin_set, safe_place, sculpt per dettagli
"""

# ── CYLINDER (tazze, barattoli) ──────────────────────────────────
"""
# Preferire bmesh rings per controllo preciso del taper:
top_r  = spec["diam_top_cm"]  / 2 * 0.01
bot_r  = spec["diam_bot_cm"]  / 2 * 0.01
height = spec["height_cm"] * 0.01
# → crea rings a z=0 e z=height con raggi diversi
# → bridge per pareti, fill per fondo
"""

# ── CURVE LOOP (manici, fili) ────────────────────────────────────
"""
# Genera N punti sul percorso, estrudi sezione circolare:
for i, pt in enumerate(path_points):
    tang = calcola_tangente(path_points, i)
    ring = crea_ring_perpendicolare(pt, tang, radius, segs)
    rings.append(ring)
# → bridge anelli consecutivi
"""

# ── LATHE / REVOLUTION (vasi, bottiglie) ────────────────────────
"""
# Definisci profilo 2D (lista di (r, z) in cm * 0.01):
profile = [(r0,z0), (r1,z1), ...]
# Genera rings a ogni altezza z con raggio r
# → bridge per pareti, fill per fondo
"""

# ── DISC + INSET (piatti, coperchi) ─────────────────────────────
"""
# Rings concentrici con z diversi per creare depressioni/rilievi:
r_outer = ring(bm, OR, z_top)
r_inner = ring(bm, IR, z_top)
r_dep   = ring(bm, IR, z_top - depth)
bridge(bm, r_outer, r_inner)   # piano
bridge(bm, r_inner, r_dep)     # parete depressione
"""
```

---

## FILOSOFIA MODULARE — Le 3 Fasi Separate

Ogni oggetto complesso va costruito in **3 fasi distinte e non mescolate**.
Mescolare le fasi è la causa più comune di bug di posizionamento e materiali duplicati.

```
FASE 1 — BUILD (ogni modulo costruisce se stesso)
    ├─ input:  spec dimensionali + tecnica
    ├─ output: oggetto nominato, origin al bottom, socket_dict
    └─ regola: nessuna dipendenza da altri oggetti ancora

FASE 2 — ASSEMBLY (il coordinator posiziona i moduli)
    ├─ input:  lista oggetti + socket_dict di ognuno
    ├─ output: scena con tutti gli oggetti posizionati
    └─ regola: usa attach_to() / attach_bounds(), mai location dirette

FASE 3 — MATERIAL (materiali applicati dopo l'assembly)
    ├─ input:  gruppi di materiali + lista oggetti per gruppo
    ├─ output: tutti gli slot materiale assegnati
    └─ regola: un materiale condiviso per gruppo → nessun duplicato
```

### Interfaccia standard di ogni modulo (socket_dict)

Ogni modulo deve restituire un dizionario di socket — punti di attacco in coordinate **locali** dell'oggetto. Il coordinator usa questi socket nella fase di assembly senza dover conoscere l'implementazione interna del modulo.

```python
# Convenzione: ogni funzione build_* ritorna (obj, socket_dict)
# socket_dict: nome_socket → (x, y, z) in coordinate locali dell'oggetto

# Esempio: tazza espresso
def build_cup_body(spec) -> tuple[bpy.types.Object, dict]:
    # ... costruzione ...
    socket_dict = {
        "handle_top":    (top_r, 0, attach_top_z),   # dove si attacca il manico in alto
        "handle_bottom": (top_r, 0, attach_bot_z),   # dove si attacca il manico in basso
        "saucer_center": (0, 0, 0),                   # centro del fondo (contatto piattino)
        "rim_center":    (0, 0, height),              # centro del bordo superiore
    }
    return obj, socket_dict

def build_handle(spec) -> tuple[bpy.types.Object, dict]:
    socket_dict = {
        "attach_top":    (0, 0, loop_h / 2),    # punto di attacco superiore
        "attach_bottom": (0, 0, -loop_h / 2),   # punto di attacco inferiore
    }
    return obj, socket_dict

# FASE 2 — Assembly: il coordinator usa i socket
body_obj, body_sockets   = build_cup_body(spec["body"])
handle_obj, handle_sockets = build_handle(spec["handle"])

# Attacca handle.attach_top al body.handle_top
attach_to(handle_obj, handle_sockets["attach_top"],
          body_obj,   body_sockets["handle_top"])
# Attacca anche handle.attach_bottom al body.handle_bottom
attach_to(handle_obj, handle_sockets["attach_bottom"],
          body_obj,   body_sockets["handle_bottom"])
```

### Convenzioni di naming e origin

```python
NAMING_CONVENTION = {
    # Nome oggetto: PascalCase, parte_di_cosa
    "body":   "Cup_Body",
    "handle": "Cup_Handle",
    "saucer": "Cup_Saucer",
}

ORIGIN_CONVENTION = {
    # Tutti gli oggetti: origin al bounding-box BOTTOM
    # → z=0 nel frame locale = il punto più basso dell'oggetto
    # → semplifica safe_place(obj, 0, 0, 0) senza calcoli
    "regola": "origin sempre al bottom prima di uscire dal modulo",
    "come":   "bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY') poi correggi a bottom",
}
```

### Schema del build_plan modulare

```python
modular_build_plan = {
    "fase_1_build": [
        {"part": "body",   "fn": "build_cup_body",   "spec": {...}},
        {"part": "handle", "fn": "build_handle",     "spec": {...}},
        {"part": "saucer", "fn": "build_saucer",     "spec": {...}},
    ],
    "fase_2_assembly": [
        # ogni attach: (obj_b, socket_b, obj_a, socket_a)
        {"move": "handle", "socket_b": "attach_top",
         "onto": "body",   "socket_a": "handle_top"},
        {"move": "handle", "socket_b": "attach_bottom",
         "onto": "body",   "socket_a": "handle_bottom"},
        {"move": "saucer", "socket_b": "top_center",
         "onto": "body",   "socket_a": "saucer_center",
         "gap": -0.004},   # 4mm dentro la rientranza
    ],
    "fase_3_material": [
        {"material": "Porcelain", "applies_to": ["body", "handle", "saucer"]},
    ],
}
```

---

## STEP 3 — PIANIFICAZIONE DIPENDENZE

```python
def pianifica_ordine(spec_sheet):
    """
    Topological sort delle parti in base alle dipendenze.
    Garantisce che ogni parte sia creata dopo la sua dipendenza.
    """
    deps  = spec_sheet.get("dependencies", {})
    parts = list(spec_sheet["parts"].keys())

    # Kahn's algorithm (topological sort)
    in_degree = {p: 0 for p in parts}
    graph = {p: [] for p in parts}
    for child, parent in deps.items():
        graph[parent].append(child)
        in_degree[child] += 1

    queue  = [p for p in parts if in_degree[p] == 0]
    order  = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order   # lista ordinata: prima le parti indipendenti

# Esempio:
# spec: body (indipendente), handle (dipende da body), saucer (dipende da body)
# → ordine: [body, handle, saucer]  o  [body, saucer, handle]
```

### Regole di posizionamento:

```python
# ── METODO PREFERITO: attach_to / attach_bounds ──────────────────────────
# Precisione < 0.5 μm, funziona con oggetti ruotati, scalati, con parent.
# Disponibile in blender-arch come funzioni già testate.

POSIZIONAMENTO = {
    # Parte indipendente → origin al fondo, appoggiata a z=0
    "center":
        "safe_place(obj, 0, 0, 0, anchor='bottom')",

    # Parte sopra un'altra → usa attach_bounds (allinea bottom di B con top di A)
    "top":
        "attach_bounds(obj_b, 'bottom', obj_a, 'top', gap=0.0)",

    # Parte sotto un'altra → usa attach_bounds inverso
    "bottom":
        "attach_bounds(obj_b, 'top', obj_a, 'bottom', gap=-gap)",

    # Parte laterale → usa attach_to con punti locali espliciti
    "side":
        "attach_to(obj_b, pt_b_local, obj_a, pt_a_local)",

    # Parte che si attacca a un punto preciso (es. manico sulla tazza)
    "attached_to:X":
        "attach_to(obj_b, (0,0,z_local_b), obj_a, (r_local_a, 0, z_local_a))",
}

# Esempi pratici:
#   Cilindro sopra cubo:   attach_bounds(cyl, 'bottom', cube, 'top')
#   Manico su tazza:       attach_to(handle_top, (0,0,-loop_h/2), cup, (top_r, 0, attach_top_z))
#   Oggetto con gap 2mm:   attach_bounds(obj_b, 'bottom', obj_a, 'top', gap=0.002)

# Funzioni world-space (incluse in blender-arch ATTACH POINT SYSTEM):
#   world_bounds(obj)                          → {'min','max','center','size'} in world coords
#   attach_to(obj_b, pt_b, obj_a, pt_a, ...)  → sposta obj_b, ritorna residual (m)
#   attach_bounds(obj_b, face_b, obj_a, face_a, gap) → sposta obj_b per bbox face

# ⚠️ DEPRECATO — NON usare:
#   obj.location.z = parent_zmin - obj_height   (fragile, ignora rotation/parent)
#   stack_on_top(parent, obj)                   (non tiene conto di matrix_world)
# Usa SEMPRE world_bounds() per misurare prima di posizionare
# Mai usare obj.location direttamente senza correzione dell'offset
```

---

## STEP 4 — PIANIFICAZIONE MATERIALI E SCENA

### Raggruppamento materiali:

```python
def raggruppa_materiali(spec_sheet):
    """
    Identifica le parti che condividono lo stesso materiale.
    Evita di creare materiali duplicati.
    """
    mat_groups = {}
    for part_name, part in spec_sheet["parts"].items():
        mat = part["material"]
        # Chiave = tipo + roughness arrotondato + metallic
        key = f"{mat['type']}_{round(mat['roughness'],1)}_{round(mat['metallic'],1)}"
        if key not in mat_groups:
            mat_groups[key] = {
                "parts": [],
                "props": mat,
                "color": part["color_rgb"],
            }
        mat_groups[key]["parts"].append(part_name)
    return mat_groups

# Esempio tazza espresso → 1 solo materiale "Porcelain" per Cup+Handle+Saucer
```

### Template luci per tipo di oggetto:

> **Nota:** tutti i tipi usano AREA (orientata con `to_track_quat('-Z','Y')`).
> Rapporti: key=100%, fill=12–25%, rim=50–65%. AgX Punchy come default.
> Per oggetti dark (elettronica, metallo nero) usare preset "dark_product".

```python
# Preset di riferimento per blender-lighting (v2 — AgX + add_area())
LIGHT_PRESETS = {
    "small_object": {   # tazze, frutti, oggetti da tavolo (< 30cm)
        # key=100%, fill=25%, rim=54%
        "key":  {"type":"AREA", "energy":120, "size":0.30, "pos":(-0.30,-0.15,0.40), "color":(1.00,0.97,0.90)},
        "fill": {"type":"AREA", "energy": 30, "size":0.80, "pos":( 0.30, 0.10,0.20), "color":(0.87,0.93,1.00)},
        "rim":  {"type":"AREA", "energy": 65, "size":0.12, "pos":( 0.00, 0.28,0.30), "color":(1.00,0.97,0.90)},
        "cm":   {"view_transform":"AgX", "look":"AgX - Punchy", "exposure":-0.2},
    },
    "small_object_white": {   # porcellana, carta, ceramica chiara
        # key=100%, fill=20%, rim=40% — dim per non bruciare il bianco
        "key":  {"type":"AREA", "energy":100, "size":0.45, "pos":(-0.28,-0.14,0.38), "color":(1.00,0.97,0.92)},
        "fill": {"type":"AREA", "energy": 20, "size":1.00, "pos":( 0.32, 0.12,0.18), "color":(0.88,0.93,1.00)},
        "rim":  {"type":"AREA", "energy": 40, "size":0.12, "pos":( 0.00, 0.28,0.24), "color":(1.00,0.97,0.90)},
        "cm":   {"view_transform":"AgX", "look":"AgX - Punchy", "exposure":-0.4},
    },
    "dark_product": {   # elettronica, metallo nero, plastica dark (30–200cm)
        # key=100%, fill=12%, rim=62% — alto contrasto, rim aggressivo
        "key":  {"type":"AREA", "energy":400, "size":0.45, "pos":(-0.80,-0.40,1.20), "color":(1.00,0.97,0.90)},
        "fill": {"type":"AREA", "energy": 50, "size":1.20, "pos":( 0.80, 0.25,0.60), "color":(0.87,0.93,1.00)},
        "rim":  {"type":"AREA", "energy":250, "size":0.15, "pos":( 0.00, 1.20,0.80), "color":(1.00,0.97,0.90)},
        "cm":   {"view_transform":"AgX", "look":"AgX - High Contrast", "exposure": 0.1},
    },
    "furniture": {       # sedie, tavoli, lampade (30–200cm)
        # key=100%, fill=20%, rim=56%
        "key":  {"type":"AREA", "energy":350, "size":1.00, "pos":(-1.50,-0.80,2.00), "color":(1.00,0.97,0.90)},
        "fill": {"type":"AREA", "energy": 70, "size":2.50, "pos":( 1.50, 0.50,1.00), "color":(0.87,0.92,1.00)},
        "rim":  {"type":"AREA", "energy":200, "size":0.40, "pos":( 0.00, 2.00,1.50), "color":(1.00,0.96,0.88)},
        "cm":   {"view_transform":"AgX", "look":"AgX - Punchy", "exposure":-0.1},
    },
    "architectural": {   # stanze, edifici (> 200cm)
        "key":  {"type":"SUN",  "energy":4.5,              "pos":(5, -5, 8),          "color":(1.00,0.96,0.85)},
        "fill": {"type":"AREA", "energy":800, "size":8.0,  "pos":(-3, 2, 4),          "color":(0.55,0.75,1.00)},
        "cm":   {"view_transform":"AgX", "look":"AgX - Base", "exposure": 0.0},
    },
}

def scegli_preset_luci(spec_sheet):
    """
    Seleziona il preset luci in base alla dimensione e al tipo di materiale.
    Per oggetti dark/elettronica, il coordinator deve passare preset='dark_product'.
    """
    w = spec_sheet["real_size_cm"]["width"]
    mat_type = spec_sheet.get("dominant_material", "")
    if w >= 200:
        return "architectural"
    if w >= 30:
        if any(k in mat_type.lower() for k in ["dark","black","metal_dark","plastic_dark","electronic"]):
            return "dark_product"
        return "furniture"
    # < 30 cm
    if any(k in mat_type.lower() for k in ["white","porcelain","ceramic","paper","light"]):
        return "small_object_white"
    return "small_object"
```

### Tecniche Named — Mapping narrativo/emotivo

> Quando il contesto narrativo è noto, usa la tecnica named invece del preset generico.
> Tecniche named disponibili in **blender-lighting**: loop, rembrandt, butterfly, split,
> high_key, low_key, food_side, food_window.

```python
NAMED_TECHNIQUE_MAP = {
    # TECNICA       : (funzione blender-lighting,  ratio,    uso tipico)
    "loop":          ("light_rig_loop",           "2:1",    "product standard, ritratto lifestyle, cibo casual"),
    "rembrandt":     ("light_rig_rembrandt",      "3:1-4:1","product premium, ritratto carattere, noir leggero"),
    "butterfly":     ("light_rig_butterfly",      "2:1-2.5","beauty, gioielli, cosmetici, still life simmetrico"),
    "split":         ("light_rig_split",          "8:1+",   "dark product, thriller, automotive notte"),
    "high_key":      ("light_rig_high_key",       "1:1",    "pubblicità, lifestyle positivo, cibo fresco"),
    "low_key":       ("light_rig_low_key",        "8:1+",   "horror, villain, whisky/spirits, lusso scuro"),
    "food_side":     ("light_rig_food_side",      "2:1",    "cibo editoriale, texture, riviste gastronomia"),
    "food_window":   ("light_rig_food_window",    "2:1",    "cibo lifestyle, luce naturale da finestra"),
}

def scegli_tecnica_luci(contesto):
    """
    Seleziona la tecnica di illuminazione in base al contesto narrativo.
    contesto: stringa descrittiva (es. "product premium", "cibo fresco", "villain")
    """
    contesto = contesto.lower()
    if any(k in contesto for k in ["horror","villain","dark","noir","thriller","lusso scuro","whisky","spirits"]):
        return "low_key"
    if any(k in contesto for k in ["split","automotive","notte","night"]):
        return "split"
    if any(k in contesto for k in ["premium","carattere","drammatic","ritratto"]):
        return "rembrandt"
    if any(k in contesto for k in ["beauty","gioielli","cosmet","simmetric"]):
        return "butterfly"
    if any(k in contesto for k in ["allegro","fresco","bambini","pubblicità","high key","positivo"]):
        return "high_key"
    if any(k in contesto for k in ["cibo","food","piatto","ristorante","editoriale","gastronomia"]):
        return "food_side"
    # default
    return "loop"

# In build_plan: inserire nel campo "scene"
# "lighting_technique": "loop"   oppure   "lighting_preset": "small_object"
# Se entrambi presenti, lighting_technique ha priorità.
```

### Template camera:

```python
def calcola_camera(spec_sheet, angle_deg=35):
    """
    Posiziona la camera per inquadrare l'oggetto completo con margine.
    angle_deg: angolo di elevazione dalla orizzontale (35=3/4 view classica)
    """
    w = spec_sheet["real_size_cm"]["width"]  * 0.01   # Blender units
    h = spec_sheet["real_size_cm"]["height"] * 0.01

    # Distanza per inquadrare con focal 85mm
    # FOV 85mm su 36mm sensor: fov_v ≈ 24°
    fov_half = math.radians(12)
    diag = math.sqrt(w**2 + h**2)
    dist = (diag / 2) / math.tan(fov_half) * 1.3   # 30% margine

    import math
    az = math.radians(40)  # azimuth: leggermente di lato
    el = math.radians(angle_deg)
    cam_x = dist * math.cos(el) * math.sin(az)
    cam_y = -dist * math.cos(el) * math.cos(az)
    cam_z = dist * math.sin(el) + h / 2   # punta al centro dell'oggetto

    return {
        "location": (cam_x, cam_y, cam_z),
        "target":   (0, 0, h / 2),
        "lens":     85,
    }
```

---

## STEP 5 — BUILD PLAN OUTPUT

Il build_plan è il documento che blender-arch riceve per eseguire la modellazione.

```python
build_plan = {

    # ── METADATI ───────────────────────────────────────────────────
    "object":      spec_sheet["object"],
    "description": spec_sheet["description"],
    "complexity":  "simple | medium | complex",

    # ── SCALA ──────────────────────────────────────────────────────
    "blender_units": {
        part_name: {
            "key_dimension_1": value_in_blender_units,
            "key_dimension_2": value_in_blender_units,
            # tutti i valori già moltiplicati per 0.01
        }
        for part_name in spec_sheet["parts"]
    },

    # ── FASI DI COSTRUZIONE (Fase 1 — BUILD) ─────────────────────
    "phases": [
        {
            "phase":      1,
            "part":       "nome_parte",
            "technique":  "UV_SPHERE | CYLINDER | LATHE | CURVE_LOOP | DISC | BOX | SCULPT | build_vessel | build_shell | state_machine",
            "method_fallback": ["LATHE→build_shell", "build_vessel→geonodes"],  # catena fallback
            "depends_on": [],              # parti da creare prima (Fase 1 sola)
            "blender_units": {},           # dimensioni già convertite (×0.01)
            "features":   [],             # features geometriche da aggiungere
            "technique_notes": "...",     # istruzioni specifiche per la skill esecutiva
            # ── SOCKET DICT (Fase 2 — ASSEMBLY) ──────────────────────────
            "sockets": {
                # nome_socket: [x, y, z] in coordinate LOCALI di questo oggetto
                # Compilato dalla skill esecutiva dopo la build, usato dal coordinator per assembly
                "esempio_attach_top":    [r, 0, z_top],
                "esempio_attach_bottom": [r, 0, z_bot],
                "esempio_base_center":   [0, 0, 0],
            },
        },
        # ... una fase per ogni parte
    ],

    # ── ASSEMBLY (Fase 2) — usa i socket della Fase 1 ─────────────
    "assembly": [
        {
            "move":     "parte_da_spostare",
            "socket_b": "nome_socket_su_B",   # socket locale di B
            "onto":     "parte_di_riferimento",
            "socket_a": "nome_socket_su_A",   # socket locale di A
            "gap":      0.0,                  # offset aggiuntivo dopo il contatto [BU]
        },
        # ... un entry per ogni attacco tra parti
    ],

    # ── MATERIALI ──────────────────────────────────────────────────
    "materials": [
        {
            "name":       "NomeMateriale",
            "applies_to": ["parte1", "parte2"],  # parti che condividono il mat
            "color_linear": [r, g, b],
            "roughness":   0.0,
            "metallic":    0.0,
            "subsurface":  0.0,
            "coat":        0.0,
            "transmission": 0.0,
            "ior":         1.45,
            "notes":       "...",
        }
    ],

    # ── SCENA ──────────────────────────────────────────────────────
    "scene": {
        "camera":      {"location": [x,y,z], "target": [x,y,z], "lens": 85},
        "light_preset": "small_object | small_object_white | dark_product | furniture | architectural",
        # OPPURE (priorità su light_preset se entrambi presenti):
        "lighting_technique": "loop | rembrandt | butterfly | split | high_key | low_key | food_side | food_window",
        # loop=2:1 standard, rembrandt=3:1 premium, butterfly=2:1 beauty, split=8:1 dark,
        # high_key=1:1 allegro, low_key=8:1 noir, food_side=laterale cibo, food_window=finestra cibo
        "world_color":  [r, g, b],          # default (0.02,0.02,0.03) — quasi nero
        "world_strength": 0.12,             # default 0.10–0.20 per product shot
        "hdri_path": None,                  # se non None: usa setup_hdri_world() invece di colore solido
        "hdri_strength": 0.5,               # 0.3-0.8 ibrido (key AREA domina), 1.0-2.0 HDRI puro
        "table": {
            "enabled": True,
            "color":   [r, g, b],
            "roughness": 0.6,
        },
        # AgX color management (default Blender 4.0+)
        "view_transform": "AgX",            # mai "Filmic" su Blender 4+
        "look": "AgX - Punchy",             # "AgX - Base" | "AgX - Punchy" | "AgX - High Contrast"
        "exposure":    0.0,                 # vedi LIGHT_PRESETS per valori per preset
    },

    # ── NOTE GENERALI ──────────────────────────────────────────────
    "notes": [
        "nota tecnica 1",
        "nota tecnica 2",
    ],
}
```

---

## STEP 5b — GATE DI PIANO (`plan_validator`) — OBBLIGATORIO

> **Regola d'oro:** un `build_plan` multi-parte **NON viene mai dispacciato
> alle skill esecutive** finché la sua decomposizione non passa
> `plan_validator.validate()`. È l'analogo, a livello di *pianificazione*,
> del gate geometrico `assembly_kernel.validate()` (1 componente /
> 0 non-manifold) che blender-arch applica *dopo*. Pipeline a 2 gate:
> piano sano **prima**, geometria sana **dopo**.

**Quando:** oggetti **multi-parte** (≥2 parti / ≥1 cucitura). Per un
oggetto banale mono-metodo mono-parte (sfera, tazza) il gate è un no-op
(nessun connettore → passa) — nessuna burocrazia aggiunta.

**Cosa fare:** esprimere il `build_plan` come `Plan` e validarlo.
```python
import sys; sys.path.insert(0, r"D:\blender-claude\kernel")
import plan_validator as pv
import importlib; importlib.reload(pv)

P = pv.Plan("oggetto")
P.part("oggetto")
P.part("upper", "oggetto"); P.part("bottom", "oggetto")
# connettori = cut-line, POSSEDUTI dal padre coordinatore (non da una foglia)
P.connector("s_vq", "seam", "upper")
P.connector("s_feather", "seam", "oggetto")   # fra subtree (padre comune)
# interfacce REALI del target (da blender-research / reference): il
# validator verifica la consistenza dato questo set, NON lo inventa
P.real_interfaces = {"s_vq", "s_feather", ...}
# foglie: metodo dalla libreria + connettori sul BORDO
P.part("vamp", "upper", "assembly_kernel", ["s_vq", "s_feather"])
...
rep = pv.validate(P)
assert rep["PASS"], rep["rules"]      # GATE: blocca qui se fallisce
```

**Le 6 regole dure** (se una fallisce → NON dispacciare, ri-decomponi):
- **R1 ownership** — ogni connettore è posseduto da una parte *interna*
  (il padre coordinatore), mai da una foglia.
- **R2 shared** — seam/junction vincolati da **≥2** parti; boundary da 1.
  (<2 = sorgente non sincronizzata = bug "throat≠lacci".)
- **R3 method** — una foglia che onora un seam/junction deve usare un
  metodo a *bordo-esatto* (arch / procedural / assembly_kernel / stitch /
  lathe). **sculpt / geonodes NON possono** (displacement/scatter).
- **R4 referential** — albero/connettori coerenti.
- **R5a TERMINAZIONE** — un'interfaccia reale che **cade dentro una
  foglia** = sotto-decomposizione (il "calzino"): decomporre lì.
- **R5b PARTIZIONE** — un taglio fra fratelli che **non** è
  un'interfaccia reale = sovra-decomposizione (cucitura inventata).

**Criterio di decomposizione (R5a/R5b operativo):** un connettore =
**una discontinuità nella RICETTA** — cucitura fisica, cambio materiale,
cambio regime di curvatura (piatto↔curvo), *cambio di metodo* sono la
stessa cosa. Si taglia **esattamente** alle discontinuità di ricetta;
ci si ferma dove la ricetta è continua sull'intera parte. Le interfacce
reali si ricavano da blender-research/reference (es. lista pezzi del
bootmaking: vamp|quarter, toe-cap, throat, feather/topline/backstay).

Modulo: `D:\blender-claude\kernel\plan_validator.py` (Python puro, no
Blender). Fondamenti e prove: memoria di progetto `decomposition_paradigm.md`.

---

## ESEMPIO COMPLETO — Tazza Espresso

```python
# Input: spec_sheet dalla blender-research
# Output: build_plan per blender-arch

build_plan = {
    "object":      "espresso_cup",
    "description": "Tazzina espresso italiana, porcellana bianca, con piattino",
    "complexity":  "medium",

    "blender_units": {
        "body":   {"top_r":0.031, "bot_r":0.0225, "height":0.058,
                   "wall":0.0045, "base":0.007},
        "handle": {"loop_h":0.034, "depth":0.024, "tube_r":0.004,
                   "attach_top_z":0.048, "attach_bot_z":0.009},
        "saucer": {"outer_r":0.0575, "height":0.016,
                   "dep_r":0.028, "dep_depth":0.004},
    },

    "phases": [
        {
            "phase": 1,
            "part": "body",
            "technique": "LATHE",
            "depends_on": [],
            "position": {"method":"safe_place", "anchor":"bottom", "target":[0,0,0]},
            "features": ["tapered_walls", "thicker_base", "foot_ring", "rounded_rim"],
            "technique_notes":
                "bmesh rings: 48 segmenti, 6 ring (foot_ext, foot_int, wall_bot, "
                "wall_top, inner_bot, inner_top). Raggio varia linearmente da "
                "bot_r a top_r per il taper. Chiudi fondo con fan di triangoli.",
        },
        {
            "phase": 2,
            "part": "handle",
            "technique": "CURVE_LOOP",
            "depends_on": ["body"],
            "position": {"method":"attach", "anchor":"side",
                         "attach_top_z":0.048, "attach_bot_z":0.009},
            "features": ["d_cross_section", "semicircular_path"],
            "technique_notes":
                "Path: semicerchio in piano XZ, 20 punti, da "
                "(top_r,0,attach_top_z) a (top_r,0,attach_bot_z). "
                "Sezione: cerchio r=0.004, 10 segmenti. "
                "Tangente calcolata su 3 punti consecutivi.",
        },
        {
            "phase": 3,
            "part": "saucer",
            "technique": "DISC",
            "depends_on": ["body"],
            "position": {"method":"stack_below", "ref":"body",
                         "gap": -0.016},   # sotto il fondo della tazza
            "features": ["central_depression", "foot_ring"],
            "technique_notes":
                "bmesh rings: outer(OR,z_top), dep_out(DR+0.004,z_top), "
                "dep_in(DR,z_top), dep_bot(DR,z_top-dep_depth). "
                "Bridge per piano e pareti dep. Fan per chiudere fondo.",
        },
    ],

    "materials": [
        {
            "name":        "Porcelain",
            "applies_to":  ["body", "handle", "saucer"],
            "color_linear": [0.955, 0.940, 0.896],
            "roughness":   0.08,
            "metallic":    0.0,
            "subsurface":  0.0,
            "coat":        0.2,
            "coat_roughness": 0.05,
            "transmission": 0.0,
            "ior":         1.52,
            "notes":       "ShaderNodeMix (RGBA) per variazione noise minima (+2%)",
        },
    ],

    "scene": {
        "camera":       {"location":[0.26,-0.32,0.16], "target":[0,0,0.02], "lens":85},
        "light_preset": "small_object_white",   # porcellana bianca → preset bianco
        "world_color":  [0.02, 0.02, 0.03],
        "world_strength": 0.12,
        "table": {"enabled":True, "color":[0.08,0.05,0.03], "roughness":0.55},
        "view_transform": "AgX",
        "look": "AgX - Punchy",
        "exposure": -0.4,
    },

    "notes": [
        "SEMPRE view_layer.update() dopo cambio location prima di leggere matrix_world",
        "ShaderNodeMixRGB deprecato in Blender 5.x → usa ShaderNodeMix data_type=RGBA",
        "origin_set(ORIGIN_GEOMETRY) subito dopo ogni creazione mesh",
        "world_bounds() per verificare posizione reale prima di ogni posizionamento",
        "SHADE SMOOTH BUG: usa ob.data.shade_smooth() NON bpy.ops.object.shade_smooth() — l'operatore non rimuove sharp_face su mesh bmesh → striature su cilindri/coni. Verifica: ob.data.normals_domain deve essere 'POINT'",
        "Dopo shade_smooth: ob.data.set_sharp_from_angle(angle=math.radians(30)) per marcare edge acuti",
        "POSIZIONAMENTO PRECISO: usa attach_to() / attach_bounds() — precisione < 0.5 μm, funziona con oggetti ruotati/scalati/con parent. Definiti in blender-arch SKILL.md sezione ATTACH POINT SYSTEM",
    ],
}
```

---

## REGOLE D'ORO DEL COORDINATOR

### Responsabilità e pipeline
1. **Non sovrapporre responsabilità** — research cerca, coordinator pianifica, arch/procedural eseguono
2. **Topological sort sempre** — mai assumere l'ordine delle parti, calcolarlo
3. **Tecnica esplicita** — la skill esecutiva non sceglie la tecnica, il coordinator la decide nel build_plan
4. **Complexity gating** — se complexity=complex, suggerisci iterazioni incrementali (crea → render → verifica → continua)
5. **Gate di piano obbligatorio** — un build_plan multi-parte NON si dispaccia mai senza che `plan_validator.validate()` dia PASS (STEP 5b). Se fallisce: ri-decomponi, non modellare

### Method selection
5. **Decision tree prima della tecnica** — verifica spine → sezione variabile → influenze globali prima di scegliere LATHE o build_vessel
6. **Fallback chain nel build_plan** — ogni fase deve dichiarare `method_fallback` con max 2 alternative ordinate
7. **Mai ricominciare da zero** — prima di cambiare tecnica, seguire la fallback chain diagnosticando l'artefatto
8. **Procedural batte arch se c'è spine** — anche per oggetti "semplici" come manici curvi o tubi

### Modularità e assembly
9. **3 fasi separate** — build / assembly / material non si mescolano mai nello stesso blocco di codice
10. **Socket dict obbligatorio** — ogni modulo espone i propri punti di attacco in coordinate locali, il coordinator li usa per l'assembly senza conoscere l'implementazione interna
11. **Origin al bottom** — ogni modulo posiziona l'origin al bounding-box bottom prima di restituire l'oggetto
12. **attach_to() per ogni contatto** — mai calcolare manualmente delta_z o offset tra parti; usare sempre attach_to() / attach_bounds() con i socket dict

### Scala e materiali
13. **Scala coerente** — converti tutto in Blender units (×0.01) nel build_plan, mai nella skill esecutiva
14. **Un materiale condiviso > N identici** — raggruppa le parti per materiale nella Fase 3, non durante la build
15. **Position sempre relativa** — mai coordinate assolute hardcoded; sempre relativo a socket_a o a z=0
16. **world_bounds() prima di ogni attach** — obj.location ≠ posizione reale se ci sono rotation/scale/parent; misurare sempre in world space
17. **Note gotchas sempre presenti** — ShaderNodeMixRGB→Mix, view_layer.update(), shade_smooth() su data non su ops
