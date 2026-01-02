# TDD Status

Check the current TDD workflow status by examining marker files.

```bash
echo "=== TDD Workflow Status ===" && \
if [[ -f ~/.claude/tmp/tdd-mode ]]; then
    echo "TDD Mode: ACTIVE"
    if [[ -f ~/.claude/tmp/tdd-phase ]]; then
        phase=$(cat ~/.claude/tmp/tdd-phase)
        case "$phase" in
            1) echo "Current Phase: 1 - Requirements Gathering"
               echo "  Action: Gather requirements, then touch ~/.claude/tmp/tdd-requirements-confirmed" ;;
            2) echo "Current Phase: 2 - Interface Design"
               echo "  Action: Design interfaces, then touch ~/.claude/tmp/tdd-interfaces-designed" ;;
            3) echo "Current Phase: 3 - Test Writing"
               echo "  Action: Write tests, then touch ~/.claude/tmp/tdd-tests-approved" ;;
            4) echo "Current Phase: 4 - Implementation"
               echo "  Action: Implement until all tests pass" ;;
            *) echo "Current Phase: Unknown ($phase)" ;;
        esac
    else
        echo "Current Phase: Not set (defaulting to 1)"
    fi
    echo ""
    echo "Markers:"
    [[ -f ~/.claude/tmp/tdd-requirements-confirmed ]] && echo "  [x] Requirements confirmed" || echo "  [ ] Requirements confirmed"
    [[ -f ~/.claude/tmp/tdd-interfaces-designed ]] && echo "  [x] Interfaces designed" || echo "  [ ] Interfaces designed"
    [[ -f ~/.claude/tmp/tdd-tests-approved ]] && echo "  [x] Tests approved" || echo "  [ ] Tests approved"
    [[ -f ~/.claude/tmp/tdd-tests-passing ]] && echo "  [x] Tests passing (COMPLETE)" || echo "  [ ] Tests passing"
else
    echo "TDD Mode: INACTIVE"
    echo ""
    echo "To start TDD mode, run: /tdd"
fi
```

## Phase Overview

| Phase | Name | Goal | Marker |
|-------|------|------|--------|
| 1 | Requirements | Understand what to build | tdd-requirements-confirmed |
| 2 | Interfaces | Design structure without logic | tdd-interfaces-designed |
| 3 | Tests | Write failing tests | tdd-tests-approved |
| 4 | Implementation | Make tests pass | tdd-tests-passing |

## Commands

- `/tdd` - Start TDD mode
- `/tdd-status` - Show current status (this command)
- `/tdd-reset` - Reset TDD state and start fresh
