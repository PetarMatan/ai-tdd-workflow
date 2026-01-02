# Architecture

## Overview

The TDD Workflow system is a hook-based enforcement mechanism for Claude Code that implements Test-Driven Development through a state machine.

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Hook System                           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │
│  │  │PreToolUse│  │PostToolUse│ │   Stop   │  │SessionEnd│ │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │    │
│  └───────┼─────────────┼────────────┼──────────────┼───────┘    │
│          │             │            │              │            │
└──────────┼─────────────┼────────────┼──────────────┼────────────┘
           │             │            │              │
           ▼             ▼            ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Phase   │  │  Auto    │  │Orchestrator│ │ Cleanup  │
    │  Guard   │  │ Compile  │  │           │  │ Markers  │
    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │            │              │
         └─────────────┴────────────┴──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   Markers    │
                   │ (~/.claude/) │
                   │   tmp/       │
                   └──────────────┘
```

## Hook Flow

### PreToolUse (tdd-phase-guard.sh)

```
Write/Edit Request
        │
        ▼
┌───────────────────┐
│  TDD Mode Active? │──No──► Allow
└────────┬──────────┘
         │Yes
         ▼
┌───────────────────┐
│  Get Current Phase│
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Match File Pattern│
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Phase 1:  Phase 2:  Phase 3:  Phase 4:
 Block    Block     Block     Allow
 All      Tests     Main      All
```

### PostToolUse (auto-compile.sh / tdd-auto-test.sh)

```
Write/Edit Complete
        │
        ▼
┌───────────────────┐
│  Is Source File?  │──No──► Exit
└────────┬──────────┘
         │Yes
         ▼
┌───────────────────┐
│ TDD Phase 4?      │──No──► Auto-Compile Only
└────────┬──────────┘
         │Yes
         ▼
┌───────────────────┐
│  Compile + Test   │
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
  Pass      Fail
    │         │
    ▼         ▼
 Report    Report
 Success   Errors
```

### Stop (tdd-orchestrator.sh)

```
Claude Stops Execution
        │
        ▼
┌───────────────────┐
│  TDD Mode Active? │──No──► Exit
└────────┬──────────┘
         │Yes
         ▼
┌───────────────────┐
│  Check Phase      │
└────────┬──────────┘
         │
    ┌────┼────┬────┐
    ▼    ▼    ▼    ▼
   P1   P2   P3   P4
    │    │    │    │
    ▼    ▼    ▼    ▼
Check  Check Check Check
Marker Compile Tests Tests
       +Marker +Marker Pass
    │    │    │    │
    ▼    ▼    ▼    ▼
Block/ Advance Block/ Complete
Advance Phase  Advance +Cleanup
```

## State Machine

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────┴───┐
│ Inactive│──►│ Phase 1 │──►│ Phase 2 │──►│ Phase 3 │──►│ Phase 4 │
└─────────┘   │ Require │   │Interface│   │  Tests  │   │ Implmnt │
   /tdd       │  ments  │   │ Design  │   │ Writing │   │  Loop   │
              └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
                   │             │             │             │
                   ▼             ▼             ▼             ▼
              requirements  interfaces    tests         tests
              -confirmed    -designed    -approved     -passing
                                                           │
                                                           ▼
                                                       Cleanup
                                                      (return to
                                                       Inactive)
```

## Marker Files

Located in `~/.claude/tmp/`:

| File | Purpose | Created By |
|------|---------|------------|
| `tdd-mode` | Indicates TDD mode is active | `/tdd` skill |
| `tdd-phase` | Contains current phase (1-4) | Orchestrator |
| `tdd-requirements-confirmed` | Phase 1 complete | User via Claude |
| `tdd-interfaces-designed` | Phase 2 complete | User via Claude |
| `tdd-tests-approved` | Phase 3 complete | User via Claude |
| `tdd-tests-passing` | Phase 4 complete | Orchestrator |

## Configuration

### Profile Detection Priority

1. Override file (`~/.claude/tdd-override.json`)
2. Auto-detection based on project files
3. `TDD_DEFAULT_PROFILE` environment variable (optional)
4. No fallback - hooks skip if no profile detected

### Source Pattern Matching

Each profile defines patterns for:
- **Main source** - Production code
- **Test source** - Test code
- **Config files** - Build/config files (always editable)

## Error Handling

### Compilation Failures

- Error output captured and displayed to Claude
- Claude instructed to fix errors
- Loop continues until success

### Test Failures

- Test output captured and displayed
- Failing tests identified
- Claude continues implementing until all pass

### Phase Violations

- File edit blocked with explanation
- Current phase requirements shown
- Instructions for advancing phase provided
