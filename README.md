# TDD Workflow for Claude Code

A Test-Driven Development (TDD) workflow enforcement system for [Claude Code](https://claude.ai/claude-code) using hooks. This system enforces strict TDD methodology through 4 phases with user approval gates.

## Overview

This system transforms Claude Code into a TDD-enforcing pair programmer that:

- **Phase 1: Requirements** - Gathers and clarifies requirements before any code is written
- **Phase 2: Interfaces** - Designs class/method signatures with compilation verification
- **Phase 3: Tests** - Writes failing tests that define expected behavior
- **Phase 4: Implementation** - Implements code in a tight compile-test loop until all tests pass

Each phase transition requires explicit user approval, ensuring human oversight throughout the development process.

## Features

- **Multi-language Support** - Pre-configured profiles for Kotlin, TypeScript, JavaScript, Python, Go, Rust, and Java (with npm/pnpm variants)
- **Auto-detection** - Automatically detects project technology stack
- **Phase Guards** - Prevents editing wrong file types per phase
- **Auto Compile/Test** - Runs compile and test commands automatically
- **User Approval Gates** - Human confirms each phase transition
- **Clean Cleanup** - Session end automatically removes markers

## Quick Start

### Installation

**Quick install (recommended):**
```bash
curl -fsSL https://raw.githubusercontent.com/PetarMatan/tdd-workflow-claude/main/install.sh | bash
```

**Or clone and install manually:**
```bash
git clone https://github.com/PetarMatan/tdd-workflow-claude.git
cd tdd-workflow-claude
./install.sh
```

**Uninstall:**
```bash
~/.claude/tdd-workflow/uninstall.sh
# Or if you have the repo cloned:
./uninstall.sh
```

### Usage

In Claude Code, start TDD mode:

```
/tdd
```

Check status:
```
/tdd-status
```

Reset and start over:
```
/tdd-reset
```

Create a custom agent:
```
/create-agent
```

## Custom Agents

You can create custom agents that auto-load during specific TDD phases. This is useful for domain-specific guidance (e.g., an API design expert for Phase 2, or a testing specialist for Phase 3).

### Creating an Agent

Use `/create-agent` to interactively create an agent, or manually create a file in `~/.claude/agents/` with YAML frontmatter:

```markdown
---
name: API Designer
phases: [2, 3]
---

# API Designer Agent

## Role
Expert in REST API design...

## Core Expertise
- RESTful principles
- OpenAPI specification
...
```

### Phase Binding

The `phases` field in frontmatter specifies which TDD phases auto-load this agent:

| Phase | Name | Use Case |
|-------|------|----------|
| 1 | Requirements | Domain experts, business analysts |
| 2 | Interfaces | Architects, API designers |
| 3 | Tests | Testing specialists |
| 4 | Implementation | Domain developers |

Agents can bind to multiple phases: `phases: [2, 3, 4]`

When a phase starts, all matching agents are automatically loaded into context.

## TDD Workflow Phases

### Phase 1: Requirements Gathering

**Goal**: Achieve complete, unambiguous understanding of what needs to be built.

- Claude gathers requirements from the user
- Asks clarifying questions about edge cases, error handling, dependencies
- User confirms requirements are complete
- **Marker**: `touch ~/.claude/tmp/tdd-requirements-confirmed`

### Phase 2: Interface Design

**Goal**: Create the structural skeleton without business logic.

- Design class/method signatures
- Method bodies contain TODO or throw NotImplementedError
- Code must compile successfully
- User approves the interfaces
- **Marker**: `touch ~/.claude/tmp/tdd-interfaces-designed`

### Phase 3: Test Writing

**Goal**: Write tests that define expected behavior (Red phase of TDD).

- Write unit/integration tests based on requirements
- Tests must compile (but will fail when run)
- Cover happy paths, edge cases, error scenarios
- User approves the tests
- **Marker**: `touch ~/.claude/tmp/tdd-tests-approved`

### Phase 4: Implementation

**Goal**: Make all tests pass (Green phase of TDD).

- Implement business logic method by method
- Automatic compile-test loop after each change
- Continue until all tests pass
- **Auto-cleanup**: Markers removed when tests pass

## Supported Technologies

| Profile | Detection | Compile Command | Test Command |
|---------|-----------|-----------------|--------------|
| Kotlin/Maven | `pom.xml` + `*.kt` | `mvn clean compile -q` | `mvn test -q` |
| Kotlin/Gradle | `build.gradle.kts` + `*.kt` | `./gradlew compileKotlin -q` | `./gradlew test -q` |
| TypeScript/npm | `package.json` + `tsconfig.json` | `npm run build` | `npm test` |
| TypeScript/pnpm | `package.json` + `tsconfig.json` + `pnpm-lock.yaml` | `pnpm run build` | `pnpm test` |
| JavaScript/npm | `package.json` + `*.js` | `npm run build` | `npm test` |
| JavaScript/pnpm | `package.json` + `pnpm-lock.yaml` + `*.js` | `pnpm run build` | `pnpm test` |
| Python/pytest | `pyproject.toml` + `*.py` | `python -m py_compile` | `python -m pytest -q` |
| Go | `go.mod` + `*.go` | `go build ./...` | `go test ./...` |
| Rust | `Cargo.toml` + `*.rs` | `cargo build` | `cargo test` |
| Java/Maven | `pom.xml` + `*.java` | `mvn clean compile -q` | `mvn test -q` |

### Custom Configuration

Create `~/.claude/tdd-override.json` to override the active profile:

```json
{
  "activeProfile": "typescript-npm"
}
```

## Configuration

### Settings Integration

Add to your `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(mkdir -p ~/.claude/tmp:*)",
      "Bash(touch ~/.claude/tmp/:*)",
      "Bash(rm -f ~/.claude/tmp/tdd-*:*)",
      "Bash(cat ~/.claude/tmp/:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/tdd-workflow/hooks/tdd-phase-guard.sh",
          "timeout": 5000
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/tdd-workflow/hooks/auto-compile.sh",
          "timeout": 120000
        }]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/tdd-workflow/hooks/tdd-auto-test.sh",
          "timeout": 300000
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/tdd-workflow/hooks/tdd-orchestrator.sh",
          "timeout": 120000
        }]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/tdd-workflow/hooks/cleanup-markers.sh",
          "timeout": 5000
        }]
      }
    ]
  }
}
```

## Testing

The project includes a comprehensive test suite using [bats](https://github.com/bats-core/bats-core) (Bash Automated Testing System).

### Running Tests

```bash
# Install bats (if not installed)
brew install bats-core    # macOS
apt install bats          # Debian/Ubuntu

# Run all tests
./tests/run_tests.sh

# Run specific test categories
./tests/run_tests.sh --unit         # Unit tests only
./tests/run_tests.sh --hooks        # Hook tests only
./tests/run_tests.sh --integration  # Integration tests only

# Verbose output
./tests/run_tests.sh --verbose
```

### Test Structure

- **Unit tests** (`tests/unit/`) - Test individual library functions
- **Hook tests** (`tests/hooks/`) - Test each hook in isolation
- **Integration tests** (`tests/integration/`) - Test full workflow scenarios

## File Structure

```
tdd-workflow-claude/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── install.sh
├── uninstall.sh
├── hooks/
│   ├── tdd-orchestrator.sh    # Stop hook - main phase controller
│   ├── tdd-phase-guard.sh     # PreToolUse - blocks wrong file types
│   ├── tdd-auto-test.sh       # PostToolUse - compile+test in Phase 4
│   ├── auto-compile.sh        # PostToolUse - auto-compile after changes
│   ├── cleanup-markers.sh     # SessionEnd - cleans up markers
│   └── lib/
│       ├── log.sh             # Shared logging library
│       ├── config.sh          # Configuration and profile detection
│       └── agents.sh          # Agent discovery and loading
├── agents/
│   ├── tdd-developer.md       # Main TDD workflow agent
│   ├── tester.md              # Testing agent
│   └── uncle-bob.md           # Clean code principles agent
├── skills/
│   ├── tdd.md                 # /tdd skill - start TDD mode
│   ├── tdd-status.md          # /tdd-status skill - show status
│   ├── tdd-reset.md           # /tdd-reset skill - reset state
│   └── create-agent.md        # /create-agent skill - generate custom agents
├── config/
│   ├── tdd-config.json        # Technology profiles configuration
│   └── settings.example.json  # Example Claude Code settings
├── tests/
│   ├── run_tests.sh           # Test runner script
│   ├── test_helper.bash       # Shared test utilities
│   ├── unit/                  # Unit tests
│   ├── hooks/                 # Hook tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures and mocks
├── .github/
│   └── workflows/
│       └── test.yml           # CI workflow
└── docs/
    ├── architecture.md
    └── troubleshooting.md
```

## State Machine

The TDD workflow is a state machine controlled by marker files in `~/.claude/tmp/`:

```
[Start] ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 4 ─► [Done]
            │          │          │          │
            ▼          ▼          ▼          ▼
    requirements  interfaces   tests     tests
    -confirmed    -designed   -approved  -passing
```

| Marker File | Meaning |
|-------------|---------|
| `tdd-mode` | TDD mode is active |
| `tdd-phase` | Current phase number (1-4) |
| `tdd-requirements-confirmed` | Phase 1 complete |
| `tdd-interfaces-designed` | Phase 2 complete |
| `tdd-tests-approved` | Phase 3 complete |
| `tdd-tests-passing` | Phase 4 complete (triggers cleanup) |

## Troubleshooting

### TDD mode not activating

Check that markers can be created:
```bash
mkdir -p ~/.claude/tmp
touch ~/.claude/tmp/test-marker
rm ~/.claude/tmp/test-marker
```

### Hooks not running

Verify hooks are installed:
```bash
ls -la ~/.claude/tdd-workflow/hooks/
```

Check Claude Code settings:
```bash
cat ~/.claude/settings.json | grep tdd
```

### Profile not detected

Force a specific profile in `~/.claude/tdd-override.json`:
```json
{
  "activeProfile": "kotlin-maven"
}
```

### Stuck in a phase

Reset and start over:
```
/tdd-reset
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Inspired by:
- Robert C. Martin's (Uncle Bob) TDD principles
- Kent Beck's Test-Driven Development methodology
- Claude Code hooks system
