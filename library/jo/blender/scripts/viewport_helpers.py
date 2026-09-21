"""
Viewport helper functions for Blender MCP.
Multi-angle screenshot inspection utilities.

Usage: Copy and paste these functions into Blender MCP execute_blender_code calls.
"""

import bpy
import math
from mathutils import Vector


def set_viewport_angle(azimuth_deg, elevation_deg, distance, target=(0, 0, 0)):
    """
    Set the 3D viewport to a specific camera angle.

    Args:
        azimuth_deg: Horizontal angle in degrees (0=right, 90=back, 180=left, 270=front)
        elevation_deg: Vertical angle in degrees (0=ground level, 90=top-down)
        distance: Distance from target
        target: (x, y, z) point to look at
    """
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            r3d = area.spaces[0].region_3d
            az = math.radians(azimuth_deg)
            el = math.radians(elevation_deg)
            eye = Vector((
                distance * math.cos(el) * math.cos(az),
                distance * math.cos(el) * math.sin(az),
                distance * math.sin(el)
            ))
            r3d.view_location = Vector(target)
            r3d.view_distance = distance
            direction = -eye.normalized()
            r3d.view_rotation = direction.to_track_quat('-Z', 'Y')
            r3d.view_perspective = 'PERSP'
            break


def four_angle_inspection(distance=1.05, target=(0, 0, 0.02)):
    """
    Set up the 4 standard inspection angles. Call this, then take a screenshot
    after each angle change.

    Returns list of (name, azimuth, elevation) tuples.
    """
    return [
        ("Reference (front-right)", -45, 55),
        ("Side view (right)", 0, 12),
        ("Front-left", 225, 35),
        ("Top-down", 5, 85),
    ]


def save_milestone(filepath):
    """Save current state as a milestone .blend file."""
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    print(f"Milestone saved: {filepath}")


def restore_milestone(filepath):
    """Restore a previously saved milestone."""
    bpy.ops.wm.open_mainfile(filepath=filepath)
    print(f"Milestone restored: {filepath}")


def delete_objects_by_prefix(prefix):
    """Delete all objects whose name starts with the given prefix."""
    to_delete = [obj for obj in bpy.data.objects if obj.name.startswith(prefix)]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in to_delete:
        obj.select_set(True)
    bpy.ops.object.delete()
    print(f"Deleted {len(to_delete)} objects with prefix '{prefix}'")
    return len(to_delete)


def set_rendered_viewport():
    """Switch viewport to Cycles rendered mode."""
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'
    bpy.context.scene.cycles.samples = 64
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces[0].shading.type = 'RENDERED'
            break


def set_material_viewport():
    """Switch viewport to Material Preview mode (faster than Rendered)."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces[0].shading.type = 'MATERIAL'
            break
