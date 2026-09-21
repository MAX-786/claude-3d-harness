---
description: >
  Skill di ricerca e analisi di riferimento per la modellazione 3D in Blender.
  Da usare PRIMA di blender-arch quando la richiesta è vaga o mancano dettagli.
  Decompone l'oggetto in parti, cerca dati reali (dimensioni, colori, materiali,
  proporzioni) per ogni parte, e produce uno spec_sheet strutturato pronto
  per blender-arch o blender-space.
  Trigger: "voglio creare un/una [oggetto]" senza dettagli specifici.
allowed-tools:
  - WebSearch
  - WebFetch
  - Read
  - Write
---

# Skill: Blender Research — Reference Data Collection

Sei un ricercatore di riferimenti per la modellazione 3D. Il tuo obiettivo è
trasformare una richiesta vaga in un `spec_sheet` preciso e completo che un
modellatore (blender-arch) può usare direttamente senza indovinare nulla.

---

## QUANDO USARE QUESTA SKILL

Usa questa skill PRIMA di blender-arch quando:
- La richiesta manca di dimensioni specifiche ("crea una mela")
- Non sono specificati colori / materiali / finiture
- L'oggetto ha più parti la cui geometria non è ovvia
- Il livello di dettaglio richiesto è realistico (non cartoon/stilizzato)

**Non serve** se l'utente ha già dato tutte le specifiche (dimensioni, colori,
materiali espliciti).

---

## PIPELINE IN 3 FASI

```
FASE 1 — DECOMPOSIZIONE
  Analizza la richiesta → identifica tutte le parti dell'oggetto
  Output: parts_list con ruolo di ogni parte

FASE 2 — RICERCA (una per parte)
  Per ogni parte: WebSearch → dati reali
  Output: dati grezzi per parte

FASE 3 — SPEC SHEET
  Struttura i dati in un dict Python pronto per blender-arch
  Output: spec_sheet completo
```

---

## FASE 1 — DECOMPOSIZIONE

Prima di cercare qualsiasi cosa, scomponi mentalmente l'oggetto:

```
Oggetto: [nome]
├── Parte principale (body/hull/frame...)
├── Parti secondarie (stem, handle, wheel...)
├── Dettagli (texture, pattern, markings...)
└── Materiali per parte
```

**Query di decomposizione** (opzionale, per oggetti complessi):
```
WebSearch: "[oggetto] anatomy parts labeled diagram"
WebSearch: "[oggetto] components breakdown"
```

**Regola**: se l'oggetto ha più di 3 parti, crea una voce separata per ognuna.
Se ha 1-2 parti, puoi unire in un'unica ricerca.

---

## FASE 2 — RICERCA PER PARTE

Per ogni parte, esegui queste query nell'ordine indicato.
Fermati quando hai i dati necessari (non sempre servono tutte).

### 2a. Dimensioni e proporzioni
```
WebSearch: "[oggetto] [parte] dimensions centimeters"
WebSearch: "[oggetto] [parte] size average measurements"
WebSearch: "[oggetto] average size weight specifications"
```
**Dati da estrarre**: lunghezza, larghezza, altezza, diametro (in cm o mm).
**Converti sempre in cm** per uniformità. Blender usa metri: 1cm = 0.01 unità.

### 2b. Colore e aspetto
```
WebSearch: "[oggetto] [parte] color varieties RGB hex"
WebSearch: "[oggetto] [parte] surface appearance texture"
```
**Dati da estrarre**: colore dominante (RGB o hex), variazioni di colore,
pattern/sfumature, colore in ombra vs luce.

### 2c. Materiale e superficie
```
WebSearch: "[oggetto] [parte] material surface properties"
WebSearch: "[oggetto] [parte] glossy matte rough smooth"
```
**Dati da estrarre**: tipo materiale (plastica, legno, metallo, organico...),
lucentezza (matte/glossy), rugosità percepita, trasparenza se rilevante.

### 2d. Forma e geometria
```
WebSearch: "[oggetto] [parte] shape geometry cross section"
WebSearch: "[oggetto] [parte] reference photo side view"
```
**Dati da estrarre**: forma della sezione trasversale, curve caratteristiche,
simmetria, features geometriche distintive (dimple, nervature, bevel, ecc.).

---

## FASE 3 — SPEC SHEET

Struttura tutto in questo formato Python. Ogni campo che non riesci a trovare
lascialo con un valore di default ragionevole commentato con `# estimated`.

```python
spec_sheet = {

    # ── METADATI ───────────────────────────────────────────────────
    "object":       "[nome oggetto]",
    "description":  "[descrizione sintetica dell'aspetto]",
    "sources":      ["url1", "url2"],   # URL delle fonti usate

    # ── SCALA GLOBALE ───────────────────────────────────────────────
    # Blender usa METRI. Scala: 1 cm reale = 0.01 unità Blender.
    # Indica le dimensioni di riferimento in cm, poi applica * 0.01
    "real_size_cm": {
        "width":  0.0,    # larghezza totale oggetto
        "height": 0.0,    # altezza totale oggetto
        "depth":  0.0,    # profondità/spessore totale
    },
    "blender_scale": 0.01,  # moltiplicatore cm → unità Blender

    # ── PARTI ───────────────────────────────────────────────────────
    "parts": {

        "nome_parte": {
            # Geometria
            "shape":        "[forma base: sphere, cylinder, cone, organic...]",
            "width_cm":     0.0,
            "height_cm":    0.0,
            "depth_cm":     0.0,
            "proportions":  {},   # es: {"width_to_height": 1.15}

            # Posizione relativa all'oggetto principale
            "position":     "[top | bottom | side | center | attached_to:X]",
            "offset_cm":    [0.0, 0.0, 0.0],   # [x, y, z] dal centro

            # Colore (linear RGB, non sRGB — Blender usa linear)
            "color_rgb":    [0.0, 0.0, 0.0],   # valore in [0,1] linear
            "color_notes":  "[varietà, sfumature, variazioni]",

            # Materiale Principled BSDF
            "material": {
                "type":         "[organic | metal | plastic | wood | glass | fabric]",
                "roughness":    0.5,    # 0=specchio, 1=completamente matte
                "metallic":     0.0,    # 0=dielettrico, 1=metallo
                "subsurface":   0.0,    # 0=opaco, >0=traslucido (pelle, frutta)
                "coat":         0.0,    # 0=niente, >0=strato lucido sopra
                "transmission": 0.0,   # 0=opaco, 1=trasparente
                "ior":          1.45,  # indice rifrazione (vetro=1.5, acqua=1.33)
                "notes":        "[note aggiuntive sulla superficie]",
            },

            # Features geometriche speciali
            "features":     [],  # es: ["dimple_top", "ridges", "flat_base", "tapered"]

            # Ordine di modellazione (1=prima, 2=dopo, ecc.)
            "model_order":  1,
        },

    },

    # ── ORDINE DI MODELLAZIONE ───────────────────────────────────────
    # Lista delle parti nell'ordine in cui vanno create in Blender
    "modeling_order": ["parte1", "parte2", "parte3"],

    # ── DIPENDENZE ──────────────────────────────────────────────────
    # Quale parte dipende da quale (per il posizionamento)
    "dependencies": {
        "parte2": "parte1",  # parte2 si attacca a parte1
    },

    # ── NOTE PER IL MODELLATORE ─────────────────────────────────────
    "modeling_notes": [
        "[nota tecnica 1]",
        "[nota tecnica 2]",
    ],
}
```

---

## CONVERSIONE COLORE: sRGB → Linear

Le fonti web danno colori in sRGB (hex o 0-255). Blender vuole **linear RGB**.

```python
def srgb_to_linear(c):
    """Converti un canale sRGB [0,1] in linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def hex_to_linear(hex_str):
    """Converti hex sRGB (#RRGGBB) in linear RGB tuple per Blender."""
    hex_str = hex_str.lstrip('#')
    r, g, b = [int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b))

# Esempi comuni già convertiti:
COLOR_REF = {
    # Frutta
    "apple_red":        (0.467, 0.009, 0.005),  # #D2042D sRGB
    "apple_green":      (0.060, 0.215, 0.010),  # #4CAF50 sRGB
    "banana_yellow":    (0.871, 0.702, 0.008),  # #FFE135 sRGB
    "orange_fruit":     (0.871, 0.322, 0.008),  # #FF8C00 sRGB
    "lemon_yellow":     (0.871, 0.871, 0.008),  # #FFFF00 sRGB

    # Legno
    "wood_light":       (0.325, 0.160, 0.063),
    "wood_dark":        (0.096, 0.040, 0.012),

    # Metalli
    "steel_gray":       (0.400, 0.400, 0.400),
    "gold":             (0.871, 0.620, 0.072),
    "copper":           (0.620, 0.209, 0.063),

    # Organici
    "leaf_green":       (0.032, 0.159, 0.008),
    "skin_medium":      (0.593, 0.271, 0.141),
    "brown_stem":       (0.096, 0.040, 0.008),
}
```

---

## ROUGHNESS: tabella di riferimento

| Superficie | Roughness | Note |
|------------|-----------|------|
| Specchio perfetto | 0.00 | |
| Metallo lucidato | 0.05 | acciaio, cromo |
| Cera / vernice auto | 0.08 | |
| Frutta (mela, pera) | 0.12–0.18 | cera naturale |
| Plastica lucida | 0.15 | ABS, acrilico |
| Porcellana | 0.10 | |
| Legno verniciato | 0.25 | parquet |
| Foglia (pianta) | 0.30 | |
| Pelle umana | 0.40 | |
| Carta | 0.55 | |
| Legno grezzo | 0.65 | |
| Tessuto | 0.70–0.85 | |
| Cemento | 0.80 | |
| Terra / suolo | 0.90 | |
| Chalk / gesso | 0.95 | |

---

## ESEMPIO COMPLETO — Mela (Apple)

```python
# Ricerche effettuate:
# - "apple average dimensions centimeters" → diam 7-8cm, h 6-7cm
# - "apple stem length diameter" → 2-4cm lunghezza, 3-5mm diam
# - "apple color Red Delicious RGB" → #9B1B30 = scuro, #DC143C = brillante
# - "apple surface waxy glossy roughness" → cera naturale, molto lucida
# - "apple leaf dimensions" → 6-12cm lunghezza, 3-5cm larghezza

spec_sheet = {
    "object": "apple",
    "description": "Red Delicious apple — frutto tondo-oblato, rosso brillante, lucido",
    "sources": [
        "https://en.wikipedia.org/wiki/Apple",
        "https://www.engineeringtoolbox.com",
    ],

    "real_size_cm": {"width": 7.5, "height": 6.5, "depth": 7.5},
    "blender_scale": 0.01,

    "parts": {

        "body": {
            "shape": "oblate sphere (schiacciata verticalmente)",
            "width_cm":  7.5,
            "height_cm": 6.5,
            "depth_cm":  7.5,
            "proportions": {"width_to_height": 1.15},
            "position": "center",
            "offset_cm": [0, 0, 0],

            "color_rgb": [0.467, 0.009, 0.005],   # #D2042D converted
            "color_notes": "rosso brillante, sfumatura giallo-verde sul lato ombra",

            "material": {
                "type": "organic",
                "roughness":   0.15,   # cera naturale
                "metallic":    0.0,
                "subsurface":  0.10,   # carne traslucida
                "coat":        0.35,   # strato ceroso sopra
                "transmission": 0.0,
                "ior": 1.45,
                "notes": "coat roughness 0.06 (molto lucido), subsurface color rosa-arancio",
            },

            "features": [
                "dimple_top",           # cavità al polo nord dove entra lo stelo
                "dimple_bottom",        # piccola cavità al polo sud
                "5_ridges_vertical",    # Red Delicious ha 5 rilievi verticali
                "flat_base",            # base leggermente appiattita
            ],
            "model_order": 1,
        },

        "stem": {
            "shape": "tapered cylinder (più stretto in cima)",
            "width_cm":  0.35,   # diametro base 3.5mm
            "height_cm": 2.8,    # lunghezza media
            "depth_cm":  0.35,
            "proportions": {"taper_ratio": 0.7},  # cima = 70% base
            "position": "top",
            "offset_cm": [0.1, 0, 3.25],  # dentro il dimple, leggermente inclinato

            "color_rgb": [0.036, 0.014, 0.003],   # marrone scuro
            "color_notes": "marrone-verde nella parte bassa, marrone scuro in cima",

            "material": {
                "type": "organic",
                "roughness":  0.88,
                "metallic":   0.0,
                "subsurface": 0.0,
                "coat":       0.0,
                "transmission": 0.0,
                "notes": "leggermente rugoso, opaco",
            },

            "features": ["slight_curve", "tapered"],
            "model_order": 2,
        },

        "leaf": {
            "shape": "flat oval with pointed tip and serrated edge",
            "width_cm":  3.5,
            "height_cm": 0.05,   # spessore foglia
            "depth_cm":  8.0,    # lunghezza
            "proportions": {"length_to_width": 2.3},
            "position": "attached_to:stem",
            "offset_cm": [0, 0, 1.5],  # a metà dello stelo

            "color_rgb": [0.027, 0.149, 0.007],   # verde foglia
            "color_notes": "verde medio sul fronte, verde più chiaro sul retro",

            "material": {
                "type": "organic",
                "roughness":   0.35,
                "metallic":    0.0,
                "subsurface":  0.15,   # foglia traslucida alla luce
                "coat":        0.05,
                "transmission": 0.0,
                "notes": "nervatura centrale visibile, texture superficiale fine",
            },

            "features": ["serrated_edge", "center_vein", "slight_curl"],
            "model_order": 3,
        },
    },

    "modeling_order": ["body", "stem", "leaf"],

    "dependencies": {
        "stem": "body",   # lo stelo parte dal dimple del corpo
        "leaf": "stem",   # la foglia si attacca allo stelo
    },

    "modeling_notes": [
        "Blender units: 7.5cm = 0.075u (width), 6.5cm = 0.065u (height)",
        "Sfera UV base: radius=0.0375, poi scale z * 0.867 (6.5/7.5)",
        "Red Delicious ha 5 lobi al polo inferiore — caratteristica distintiva",
        "Dimple superiore: brush sculpt, radius=0.015u, depth=-0.008u",
        "Coat layer: Coat Weight=0.35, Coat Roughness=0.06",
        "Subsurface Radius: (0.05, 0.02, 0.01) — rosso con tocco arancio",
        "origin_set(ORIGIN_GEOMETRY) subito dopo la creazione",
    ],
}
```

---

## TEMPLATE QUERY PER TIPO DI OGGETTO

### Oggetti organici (frutta, verdura, piante)
```
"[oggetto] average size dimensions cm"
"[oggetto] color varieties RGB"
"[oggetto] surface texture waxy matte glossy"
"[oggetto] anatomy cross section"
```

### Oggetti meccanici / industriali
```
"[oggetto] technical specifications dimensions"
"[oggetto] material composition"
"[oggetto] surface finish treatment"
"[oggetto] engineering drawing blueprint"
```

### Mobili / architettura
```
"[oggetto] standard dimensions cm"
"[oggetto] wood type finish"
"[oggetto] design reference front side view"
```

### Veicoli
```
"[oggetto] dimensions length width height"
"[oggetto] body panels material"
"[oggetto] color coat paint layers"
"[oggetto] wheel tire dimensions"
```

### Cibo / cucina
```
"[oggetto] food dimensions average size"
"[oggetto] color appearance texture"
"[oggetto] ingredients visible components"
```

---

## OUTPUT FINALE

Dopo aver completato le 3 fasi, presenta il risultato così:

```
## Spec Sheet: [Nome Oggetto]

**Dimensioni reali**: W×H×D in cm
**Parti identificate**: N

### [Parte 1]
- Forma: ...
- Dimensioni: ...
- Colore (linear RGB): (r, g, b)
- Roughness: X | Subsurface: Y | Coat: Z
- Features: [lista]

### [Parte 2]
...

### Note di modellazione
- [nota 1]
- [nota 2]

### Pronto per blender-arch
[spec_sheet come dict Python, copiabile direttamente nello script]
```

---

## REGOLE D'ORO

1. **Cerca prima, modella dopo** — mai iniziare a scrivere codice Blender senza lo spec_sheet
2. **Fonti multiple** — almeno 2 fonti per le dimensioni (possono variare)
3. **Valori medi** — se trovi range, usa il valore mediano
4. **Linear RGB** — converti sempre da sRGB prima di mettere nello spec_sheet
5. **Stima commentata** — se non trovi un dato, metti `# estimated` e un valore ragionevole
6. **Dipendenze esplicite** — specifica sempre quale parte si attacca a quale
7. **modeling_order** — la parte principale (body/frame) sempre prima
8. **Scala coerente** — tutti i valori in cm, poi `* 0.01` per Blender units
