# Task classifier

Decides the profile: `fast`, `standard` or `cinematic`. The profile controls two
things only: which workflow stages run (stages carry a `min_profile`) and how
much iteration the job may spend (`budgets` in `registry/profiles.yaml`). It is a
cost decision as much as a quality one, because a cinematic job reads a dozen
long skills and renders many previews.

## Signals

Count what the request actually contains, not how enthusiastic it sounds.

| Dimension | fast | standard | cinematic |
| --- | --- | --- | --- |
| Subjects | one object, or one change | a handful of objects | an environment, many asset types |
| Surroundings | none, or whatever is already there | a simple set: floor, backdrop, a few props | a full place with depth |
| Look | plausible | believable materials and light | photoreal or a named film look |
| Light | default presentation light | designed lighting | atmosphere: volumetrics, weather, night, practicals |
| Camera | any readable angle | composed still | moving camera, or a named lens and format |
| Deliverable | a model or a quick image | one finished image or one short spin | a hero frame, a sequence, or both |

Take the highest column that has **two or more** matches. One stray word does not
move a job up: "a cinematic-looking mug" is still one object and stays `fast`
or `standard`.

## Examples

| Request | Profile | Why |
| --- | --- | --- |
| Make a simple wooden table | fast | one object, no set |
| Make the lamp shade red | fast | edit to an existing scene |
| Model a low-poly sword and export it as GLB | fast | one object, export is cheap |
| Create a realistic bedroom | standard | several objects, designed light, one still |
| Product photo of this watch on a marble surface | standard | one hero object plus a set, composed still |
| Turntable of the headphones, looping | standard | one object, a camera move, one deliverable |
| Desk setup with monitor, plant and lamp at dusk | standard | handful of objects, designed light |
| Photorealistic rainy Tokyo street at night, 35mm | cinematic | environment, weather, night, named lens |
| Medieval village at sunset, camera drifting through | cinematic | environment, atmosphere, moving camera |
| Traditional Japanese room in heavy rain, camera moving toward the window | cinematic | interior environment, weather, camera move |

## Tie-breaks

- **Between two profiles, take the lower one** and tell the user in one line
  ("Treating this as standard; say the word if you want the cinematic pass").
  Moving up later costs one more resolve; starting too high wastes the budget.
- **The user's words override the signals.** "Quick", "rough", "just block it
  out" force `fast`. "Go all out", "portfolio piece", "final" allow `cinematic`.
- **Edits inherit nothing.** A small change to a cinematic scene is a `fast` job
  with ad hoc capabilities, not a cinematic one.

## Changing profile mid-job

If the job turns out bigger than classified (a "simple shelf" that needs a room
around it to read), say so, re-run `resolve` at the higher profile, and carry on
from the current scene: the higher profile adds stages, it does not restart the
build. If the user asks to wrap up early, finish the current stage, render at the
`fast` final budget and report what was skipped.
