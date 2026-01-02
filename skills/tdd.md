# TDD Mode Activation

**MANDATORY FIRST STEP** - Execute this command IMMEDIATELY to activate TDD mode:

```bash
mkdir -p ~/.claude/tmp && echo "1" > ~/.claude/tmp/tdd-phase && touch ~/.claude/tmp/tdd-mode
```

After executing the command above, load the TDD developer agent from the installed location or use the built-in guidance below.

---

## TDD Workflow Activated

You are now in **Test-Driven Development** mode. The workflow enforces these phases:

1. **Phase 1: Requirements** - Gather and clarify requirements with user
2. **Phase 2: Interfaces** - Create class/method skeletons (no logic)
3. **Phase 3: Tests** - Write failing tests, get user approval
4. **Phase 4: Implementation** - Autonomous loop until tests pass

**Current Phase: 1 - Requirements Gathering**

## Phase Markers

To advance through phases, create these markers after user approval:

- Phase 1 -> 2: `touch ~/.claude/tmp/tdd-requirements-confirmed`
- Phase 2 -> 3: `touch ~/.claude/tmp/tdd-interfaces-designed`
- Phase 3 -> 4: `touch ~/.claude/tmp/tdd-tests-approved`

## Getting Started

Begin by asking the user to describe the feature they want to implement. Ask clarifying questions for any ambiguities.

**Required Questions:**
1. What is the feature/functionality needed?
2. What are the expected inputs and outputs?
3. What error scenarios should be handled?
4. Are there any edge cases to consider?
5. What external dependencies are involved?

Once requirements are clear and user confirms, create the requirements marker and proceed to interface design.
