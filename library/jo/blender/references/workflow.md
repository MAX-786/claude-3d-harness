# Blender Design Workflow

## Phase 1: Understand the Target

Before writing any code:

1. If user provides a reference image, describe what you see in plain terms
2. Ask clarifying questions:
   - Is the base flat or curved?
   - Is the feature centered or offset?
   - Are elements parallel or concentric?
   - What are the approximate proportions?
3. Break the design into 2-3 simple geometric parts
4. State your plan to the user and confirm before building

## Phase 2: Scene Setup

1. Clear the scene or create a new file
2. Set up Cycles rendering with GPU
3. Add key + fill area lights
4. Add a floor plane with neutral material
5. Set world background to warm neutral
6. Switch viewport to Material Preview or Rendered mode

## Phase 3: Build Part by Part

For each part of the design:

1. Save a milestone FIRST
2. Build the simplest version
3. Apply material
4. Take 4-angle screenshots:
   - Reference angle (front-right, elevated)
   - Side view (low angle — critical for checking flatness vs dome)
   - Opposite side (front-left or back)
   - Top-down
5. Compare to reference and describe what matches/doesn't
6. Get user feedback before moving on

## Phase 4: Iterate

When user requests changes:

1. Save a milestone
2. Make ONLY the requested change
3. Take multi-angle screenshots
4. Show the user
5. Repeat until approved

## Phase 5: Polish

Once the form is approved:

1. Refine materials (texture scale, roughness, color)
2. Adjust lighting for best presentation
3. Fine-tune camera angle to match reference
4. Add final details (plants, accessories) if requested

## Key Rules

- ALWAYS save milestones before changes
- ALWAYS take multi-angle screenshots to verify
- NEVER skip the side view (catches dome vs flat)
- NEVER change multiple things at once
- NEVER overthink the math — start with user's plain description
- If the user says "revert," restore the milestone immediately
