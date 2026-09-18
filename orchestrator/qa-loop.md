# Render, inspect, refine

The harness owns *when* to check, *how much* to spend and *when to stop*. What
to look for in an image belongs to the upstream skills: the visual validation
checkpoint in the execution-core skill, the critique protocol in
pipeline-planning, and the contact-sheet review in animation-qa.

## Checkpoints

The profile's `checkpoints` budget says when to look:

| Profile | Look after |
| --- | --- |
| fast | assembly (one viewport screenshot) |
| standard | block-out, lighting, materials |
| cinematic | every stage gate; for motion, a contact sheet of 8-12 frames before any full render |

At each checkpoint produce an image the cheapest way the budget allows (viewport
screenshot, then a preview render), open it, and judge it against the acceptance
criteria in the plan. A tool reporting success is not evidence: renders that
pass every numeric check can still be black, magenta, empty or framed on
nothing. Save checkpoint images in the job folder so the report can cite them.

## A refinement pass

One pass is: name one defect, state its likely cause, make the smallest change
that addresses it, produce a new image, compare with the previous one. Fix the
defect that most damages the picture first. Order that usually holds: nothing
visible or wrong subject, then scale and proportion, then framing, then
lighting, then materials, then detail and noise.

Change one thing per pass when you can. Several simultaneous changes make it
impossible to tell which one helped, and the budget is small.

## Escalation

If the same defect survives two passes, stop varying parameters. Load the
`refinement` capability: it diagnoses which dimension is failing and whether the
skills in use can fix it at all. Its steps about patching skill files,
versioning and releases do not apply here; write the lesson to
`notes/lessons.md`. If refinement points at the provider itself, this is the one
case for loading that capability's fallback.

## Stop conditions

Stop and deliver when any of these holds:

- every acceptance criterion passes;
- `refinement_passes` is spent;
- the remaining defects need something the job does not have (a paid service, an
  asset the user must supply, a decision only the user can make);
- a pass made the image worse twice in a row: restore the better state first.

Report honestly: what passed, what did not, what you would do next with more
budget. An unfinished result described accurately is more useful than one
described as done.

## Motion

Approve a still before rendering a range. Then render a sparse contact sheet at
preview quality, check it, and only then render the full frame range at the
final budget. A full-quality animation render is the most expensive step in any
job; it should never be the first time the motion is seen.
