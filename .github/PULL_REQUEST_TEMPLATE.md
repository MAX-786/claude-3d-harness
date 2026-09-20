<!-- What changes, and why. If it came out of a real job, say which. -->

## Checks

- [ ] `uv run scripts/harness.py verify --strict` reports 0 failures and 0 warnings
- [ ] `uv run --with pytest --with pyyaml pytest -q` passes
- [ ] Nothing under `upstream/` is edited, and nothing is copied out of `upstream/blender-skills` (it has no license)
- [ ] `.mcp.json` was regenerated with `harness.py mcp-config --write`, not edited by hand (only if `registry/mcp.yaml` changed)
- [ ] `claude plugin validate .` passes (only if `.claude-plugin/` or `SKILL.md` changed)
- [ ] `CHANGELOG.md` has a line under "Unreleased" (only if users will notice the change)
