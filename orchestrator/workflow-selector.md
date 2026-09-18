# Workflow selector

A workflow is an ordered list of stages, each naming one capability
(`workflows/*.yaml`). Pick exactly one per job, then shape it with `--variant`
and `--add`. `uv run scripts/harness.py list workflows` prints the match hints.

## Decision order

Ask these in order and stop at the first yes.

1. Is this a change to a scene that already exists? Use no workflow. Name the
   capabilities: `resolve -c materials lighting -p fast`.
2. Must the result match supplied reference sheets, orthographic drawings or a
   texture pack 1:1? `modeling`, plus `--add reference-reconstruction`
   (or `wireframe-to-3d`, or `logo-mascot`). Those stacks are fail-gated against
   the source and replace free modeling.
3. Is there an environment and a moving camera or heavy atmosphere? `cinematic`.
4. Is motion the deliverable? `animation`.
5. Is it one product shown for sale? `product`.
6. Is it a place? `environment`.
7. Is the request about lens, light and composition? `photography`.
8. Otherwise the object is the deliverable: `modeling`.

## Shaping a workflow

- **Variants.** Capabilities such as `camera-animation` have several providers
  for different intents. Choose with `--variant camera-animation=slow-zoom`. The
  load plan lists the variants and when each applies.
- **Alternatives.** Each workflow lists capabilities worth swapping in
  (`architecture` for a building, `sculpting` for organic detail). Add them with
  `--add <capability>`; they do not remove the default stage, so skip the stage
  they replace.
- **Optional stages** are printed with a `when` condition. They cost nothing
  unless you read them.

## Worked examples

| Request | Command |
| --- | --- |
| Simple wooden table | `resolve -w modeling -p fast` |
| Slatted oak bench, parametric spacing | `resolve -w modeling -p standard --add parametric-design` |
| Product photo of a watch, plus a seamless spin | `resolve -w product -p standard --variant camera-animation=perfect-loop` |
| Same perfume bottle in five finishes | `resolve -w product -p standard --variant look-variants=materials` |
| Realistic bedroom | `resolve -w environment -p standard` |
| Medieval village at sunset, slow move through it | `resolve -w cinematic -p cinematic --variant camera-animation=dolly-rotate` |
| Japanese room in heavy rain, push toward the window | `resolve -w cinematic -p cinematic --variant camera-animation=slow-zoom` |
| Flag waving in wind, 5 second loop | `resolve -w animation -p standard --add physics` |
| Rig this robot arm and animate a pick-up | `resolve -w animation -p standard --add rigging` |
| Match this logo sheet exactly and export GLB | `resolve -w modeling -p standard --add logo-mascot` |
| Relight the existing scene for golden hour | `resolve -c lighting rendering -p fast` |

## When nothing fits

Compose an ad hoc plan from capabilities (`resolve -c ... -p <profile>`). If the
same ad hoc combination comes up repeatedly, it has earned a file in
`workflows/`: copy the closest one, adjust the stages, run
`uv run scripts/harness.py verify`.
