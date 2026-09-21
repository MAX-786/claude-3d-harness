# Common Blender MCP Errors and Fixes

## "key 'Subsurface Color' not found"
Blender 4.x removed the Subsurface Color input from Principled BSDF.
Do NOT set `inputs['Subsurface Color']`. Use `inputs['Base Color']` instead.

## "view3d.view_selected.poll() expected a view3d region"
Cannot use `bpy.ops.view3d.*` operators without proper context override.
Fix: Use `region_3d` properties directly instead of operators.

```python
# BAD
bpy.ops.view3d.view_selected()

# GOOD
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        r3d = area.spaces[0].region_3d
        r3d.view_location = target
        r3d.view_distance = distance
        r3d.view_rotation = quaternion
        break
```

## "key 'Camera' not found"
Don't assume a Camera object exists. Always check first or use viewport controls.
```python
cam = bpy.data.objects.get('Camera')  # Returns None if not found
```

## Material disappears after rebuild
Cause: `bpy.ops.outliner.orphans_purge()` deletes materials with zero users.
During slat rebuild, the material temporarily has zero users.
Fix: NEVER call `orphans_purge`. Delete objects manually instead.

## Bowl creates a hole in geometry
Cause: Subtracting bowl depth pushes z_top below z_bot, filtering out geometry.
Fix: Use multiplicative depression.

```python
# BAD - creates holes where z_top goes negative
z_top -= bowl_depth * gaussian

# GOOD - scales down proportionally, never below z_bot
bowl_scale = 1.0 - 0.85 * gaussian
z_top = z_bot + (z_top - z_bot) * bowl_scale
```

## Dome shape when disc should be flat
Cause: Using a Gaussian radial envelope for height makes center tall and edges short.
Fix: Use uniform base height + localized features (bowl, rim) via smoothstep.

```python
# BAD - creates a dome
z_top = MAX_H * exp(-((r - R_peak)**2) / (2 * sigma**2))

# GOOD - flat disc with localized features
z_top = BASE_HEIGHT  # uniform everywhere
z_top *= edge_taper  # only taper at the very rim
```

## Code execution timeout
Large numbers of slats with high profile resolution can be slow.
Keep profile_resolution at 140 max and num_slats at 50 max for interactive work.
Use lower values (80 resolution, 30 slats) for quick previews.

## Blender MCP not responding
1. Check Blender is open and the addon is running (socket server on port 9876)
2. Check the MCP server is configured: `claude mcp add blender uvx blender-mcp`
3. Try `mcp__blender__get_scene_info` to verify connection
4. Restart Blender if the addon socket died
