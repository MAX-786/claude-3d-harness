# Surface Function Patterns

Reusable surface functions for parametric designs. All follow the same interface:
`surface_fn(x, y) -> (z_top, z_bot)` or `(None, None)` if outside boundary.

## Utility: smoothstep

Used in all patterns for smooth transitions.

```python
def smoothstep(x, edge0, edge1):
    if edge1 == edge0:
        return 0.0 if x < edge0 else 1.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)
```

## Pattern 1: Flat Disc with Raised Bowl

Circular disc with uniform height and a raised center bowl for plants.
Parameters control bowl size, wall steepness, and height.

```python
def flat_disc_with_bowl(x, y):
    R = 0.40          # disc radius
    BASE_H = 0.055    # flat disc height
    WALL_H = 0.15     # bowl wall height
    BOWL_R = 0.18     # bowl radius

    r = math.sqrt(x*x + y*y)
    if r >= R * 0.97:
        return None, None

    z_top = BASE_H
    z_bot = 0.002

    # Edge taper
    z_top *= 1.0 - smoothstep(r, R * 0.82, R * 0.96)
    if z_top < 0.004:
        return None, None

    # Steep bowl walls
    bd = math.sqrt(x*x + y*y)
    outer_rise = smoothstep(bd, BOWL_R * 1.0, BOWL_R * 0.70)
    z_top += (WALL_H - BASE_H) * outer_rise

    # Inner depression
    if bd < BOWL_R * 0.85:
        inner_dip = 1.0 - smoothstep(bd, BOWL_R * 0.15, BOWL_R * 0.65)
        z_top -= 0.12 * inner_dip
        z_top = max(z_bot + 0.003, z_top)

    return z_top, z_bot
```

## Pattern 2: Uniform Flat Disc

Simplest pattern — constant height with edge taper. Good for trays, coasters, bases.

```python
def uniform_disc(x, y):
    R = 0.40
    HEIGHT = 0.03

    r = math.sqrt(x*x + y*y)
    if r >= R * 0.97:
        return None, None
    z_top = HEIGHT * (1.0 - smoothstep(r, R * 0.85, R * 0.96))
    if z_top < 0.003:
        return None, None
    return z_top, 0.002
```

## Pattern 3: Gentle Wave Disc

Flat disc with subtle angular height variation. For organic-looking forms.

```python
def wave_disc(x, y):
    R = 0.40
    BASE_H = 0.05

    r = math.sqrt(x*x + y*y)
    if r >= R * 0.97:
        return None, None
    theta = math.atan2(y, x)

    # Subtle wave (20-30% variation)
    wave = 1.0 + 0.25 * math.sin(theta - 0.25 * math.pi)

    z_top = BASE_H * wave
    z_top *= 1.0 - smoothstep(r, R * 0.82, R * 0.96)
    if z_top < 0.003:
        return None, None
    return z_top, 0.002
```

## Pattern 4: Rectangular Base

For furniture-style flat bases (tabletops, shelves).

```python
def rectangular_base(x, y):
    W = 0.50  # width (X)
    D = 0.30  # depth (Y)
    H = 0.025 # thickness

    if abs(x) > W/2 or abs(y) > D/2:
        return None, None

    z_top = H
    # Smooth edge taper
    edge_x = 1.0 - smoothstep(abs(x), W/2 * 0.85, W/2 * 0.98)
    edge_y = 1.0 - smoothstep(abs(y), D/2 * 0.85, D/2 * 0.98)
    z_top *= edge_x * edge_y

    if z_top < 0.003:
        return None, None
    return z_top, 0.002
```

## Tips for Creating New Patterns

1. Always use multiplicative depressions, never subtractive
2. Clamp z_top: `z_top = max(z_bot + 0.001, z_top)`
3. Use smoothstep for all transitions (no discontinuities)
4. Keep z_bot constant at 0.002 (flat bottom)
5. Filter out thin geometry: `if z_top < 0.003: return None, None`
6. Test with 20 slats first, increase to 50 after verifying
