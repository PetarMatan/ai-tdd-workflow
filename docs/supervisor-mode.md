# Supervisor Mode

Supervisor mode runs each TDD phase in a fresh Claude session, preventing context accumulation that can degrade AI performance on large features.

## The Context Problem

When working on large features, a single Claude session accumulates context from all your interactions: requirements discussions, interface iterations, test debugging, implementation attempts. This context buildup has real consequences:

- **Response quality degrades** as the model juggles more information
- **Focus drifts** from the current task to past conversations
- **Token limits** eventually force session restarts, losing context anyway

For a normal feature that takes 30-60 minutes, this isn't noticeable. But for a feature that spans hours or involves complex multi-file changes, context accumulation becomes the bottleneck.

## How Supervisor Mode Solves This

Supervisor mode runs each TDD phase in a **fresh Claude session**. Instead of carrying the full conversation history, each phase starts clean with only what it needs:

```
Phase 1 (Requirements)
    │
    └─► Generates requirements summary
            │
            ▼
Phase 2 (Interfaces) ◄─── Receives only the summary
    │
    └─► Generates interfaces list
            │
            ▼
Phase 3 (Tests) ◄─── Receives requirements + interfaces
    │
    └─► Generates tests list
            │
            ▼
Phase 4 (Implementation) ◄─── Receives all summaries
```

Each session gets distilled context (what was decided) rather than full history (how it was decided). The AI focuses entirely on the current phase's goals.

## When to Use Each Mode

| Scenario | Recommended Mode | Why |
|----------|-----------------|-----|
| Quick bug fix | CLI (`/tdd`) | Overhead not worth it |
| Single-file feature | CLI (`/tdd`) | Context stays manageable |
| Multi-file feature | Either | Depends on complexity |
| Large feature (2+ hours) | Supervisor (`tdd-start`) | Prevents context degradation |
| Multi-day project | Supervisor (`tdd-start`) | Essential for quality |
| Learning/experimenting | CLI (`/tdd`) | Faster iteration |

**Rule of thumb**: If you'd normally take breaks or restart sessions due to AI getting "confused", use Supervisor mode.

## Prerequisites

Supervisor mode requires the Claude Agent SDK:

```bash
pip install claude-agent-sdk
```

The installer checks for this and will warn you if it's not installed.

## Usage

### Starting a Workflow

```bash
# From your project directory
tdd-start

# Specify a different directory
tdd-start -d ./my-project

# With an initial task description
tdd-start -t "Build a REST API for user management"
```

### During the Session

Each phase runs interactively. You converse with Claude normally as it works through the phase goals.

**Phase completion signals:**
- Type `/done`, `/complete`, or `/next` to signal you're ready for the next phase
- Claude will also detect when phase goals are met

**Abort signals:**
- Type `/quit`, `/exit`, or `/abort` to stop the workflow
- Press `Ctrl+C` to interrupt

**Phase transitions:**
At the end of each phase, you'll be asked to confirm:
```
Proceed to next phase? [y/n]
```

### Command Reference

| Command | Description |
|---------|-------------|
| `tdd-start` | Start new workflow in current directory |
| `tdd-start -d PATH` | Start in specified directory |
| `tdd-start -t "TASK"` | Start with initial task description |
| `tdd-start -h` | Show help |

## Differences from CLI Mode

| Aspect | CLI Mode | Supervisor Mode |
|--------|----------|-----------------|
| Sessions | Single | One per phase |
| Context | Accumulates | Fresh each phase |
| Best for | Small features | Large features |
| Startup | `/tdd` in Claude Code | `tdd-start` in terminal |

## Troubleshooting

### "claude-agent-sdk not installed"

```bash
pip install claude-agent-sdk
```

Or if using a virtual environment:
```bash
source your-venv/bin/activate
pip install claude-agent-sdk
```

### Session interrupted

If you interrupt a session (`Ctrl+C`), markers are automatically cleaned up. Simply start a new session when ready.

### Phase not advancing

If a phase isn't advancing, use the manual completion commands:
- `/done`, `/complete`, or `/next`

You'll then be prompted to confirm before proceeding to the next phase.
