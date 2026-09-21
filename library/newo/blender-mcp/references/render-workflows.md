# Render and visual verification

## Decide whether an image is needed

Use structured readback for names, types, dimensions, transforms, node links, settings, and revisions. Use get_viewport_screenshot only when success depends on visible appearance, composition, clipping, shading, or spatial relationships.

A viewport screenshot reflects the current viewport state. It does not prove final render-engine output, color management, animation, file output, or off-screen geometry.

## Visual acceptance loop

1. Inspect the target object or graph first.
2. Capture a before image only when comparison is useful.
3. Apply the smallest requested mutation.
4. Verify structured state.
5. Capture one after image at a useful size when appearance is part of acceptance.
6. If the image reveals a problem, identify a concrete cause before another mutation.

Avoid repeated screenshots that provide no new evidence.

## Render-sensitive automation

- Call get_runtime_automation_context before writing version-sensitive Python for render engines, movie output, compositor behavior, or Actions.
- Use version-correct Blender documentation when engine identifiers, formats, or properties are uncertain.
- Prefer existing structured node tools for compositor edits.
- Treat actual rendering as an explicit potentially long-running operation.
- Require explicit user intent before changing an output path, replacing an existing render, writing animation frames, or saving the .blend file.
- Use execute_blender_code only for render operations not represented by structured tools. Keep the code bounded and return the resolved engine, output path, frame range, and operation result.

## Motion blur on Geometry Nodes objects

For every object that carries a Geometry Nodes modifier, disable deformation motion blur only. Blender computes deformation motion blur by interpolating vertex positions, and Geometry Nodes changes vertex topology between frames, which makes that interpolation unstable and produces broken motion vectors.

- On the object, set `use_deform_motion = False` (Object Properties > Motion Blur, uncheck Deformation).
- Leave `use_motion_blur = True`: object-level transform motion blur remains stable and must not be disabled.
- Do not change scene-level or view-layer motion blur unless the user asked for that.

## Report evidence

Separate structured verification from visual judgment. State whether the result was checked in the viewport, rendered, or only validated from configuration, and state whether any output file or Blender project was written.
