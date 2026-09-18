---
name: blender-harness
description: Entry point for every 3D or Blender task in this repository - modeling, materials, lighting, cameras, rendering, animation, product shots, environments, cinematic scenes, exports. Classifies the job (fast, standard or cinematic), picks a workflow, asks the registry which upstream skills to load, then drives Blender through the single `blender` MCP server with render, inspect and refine checkpoints. Use it whenever the user asks to create, change, light, render, animate or export anything in 3D, even if they never say "Blender".
---

# Blender harness (opened as a project)

The harness's entry skill lives at the root of this repository, where the plugin
install finds it. Read `SKILL.md` in the repository root now and follow it
exactly. For this checkout:

- the harness root `H` is the repository root;
- the Blender tools are `mcp__blender__<tool>`, served from the project `.mcp.json`;
- job folders go to `output/` in the repository root.

The user's request: $ARGUMENTS

If that line is empty, the request is in the conversation.
