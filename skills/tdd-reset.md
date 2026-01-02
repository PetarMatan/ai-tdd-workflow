# TDD Reset

Reset the TDD workflow state to start fresh.

**Execute this command to clear all TDD markers:**

```bash
echo "=== Resetting TDD Workflow ===" && \
rm -f ~/.claude/tmp/tdd-mode && \
rm -f ~/.claude/tmp/tdd-phase && \
rm -f ~/.claude/tmp/tdd-requirements-confirmed && \
rm -f ~/.claude/tmp/tdd-interfaces-designed && \
rm -f ~/.claude/tmp/tdd-tests-approved && \
rm -f ~/.claude/tmp/tdd-tests-passing && \
echo "TDD markers cleared successfully." && \
echo "" && \
echo "To start a new TDD workflow, run: /tdd"
```

## What This Does

Removes all TDD state markers:
- `tdd-mode` - TDD mode activation flag
- `tdd-phase` - Current phase number
- `tdd-requirements-confirmed` - Phase 1 completion marker
- `tdd-interfaces-designed` - Phase 2 completion marker
- `tdd-tests-approved` - Phase 3 completion marker
- `tdd-tests-passing` - Phase 4 completion marker

## When to Use

- Starting a completely new feature from scratch
- Abandoning current TDD workflow
- Recovering from corrupted state
- Debugging TDD workflow issues

## After Reset

Run `/tdd` to start a new TDD workflow from Phase 1.
