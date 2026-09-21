<!-- What changes, and why. If it came out of a real job, say which. -->

## Checks

- [ ] `uv run scripts/harness.py verify --strict` reports 0 failures and 0 warnings
- [ ] `uv run --with pytest --with pyyaml pytest -q` passes
- [ ] If anything under `library/` changed: the diff was read against the checklist in `docs/security-review.md`, `harness.py audit --changed` was run, and `library/SHA256SUMS` was rewritten in the same commit
- [ ] Nothing was copied from a source without a license that allows it
- [ ] `.mcp.json` was regenerated with `harness.py mcp-config --write`, not edited by hand (only if `registry/mcp.yaml` changed)
- [ ] `claude plugin validate .` passes (only if `.claude-plugin/` or `SKILL.md` changed)
- [ ] `CHANGELOG.md` has a line under "Unreleased" (only if users will notice the change)
