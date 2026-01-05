# TDD Workflow for Claude Code

A Test-Driven Development (TDD) workflow enforcement system for [Claude Code](https://claude.ai/claude-code) using hooks. This system enforces strict TDD methodology through 4 phases with user approval gates.

## Overview

This system transforms Claude Code into a TDD-enforcing pair programmer that:

- **Phase 1: Requirements** - Gathers and clarifies requirements before any code is written
- **Phase 2: Interfaces** - Designs class/method signatures with compilation verification
- **Phase 3: Tests** - Writes failing tests that define expected behavior
- **Phase 4: Implementation** - Implements code in a tight compile-test loop until all tests pass

Each phase transition requires explicit user approval, ensuring human oversight throughout the development process.

### Framework Philosophy

**This is a framework, not a complete solution.** The TDD workflow provides structure and enforcement - it ensures Claude follows a disciplined process with clear goals and closed feedback loops. However, the *quality* of the generated code depends largely on the **agents** loaded during each phase.

The workflow itself:
- Enforces phase progression (no skipping steps)
- Provides compilation and test feedback loops
- Blocks incorrect file edits per phase
- Requires human approval at each gate

The agents determine:
- Code style and patterns used
- Architecture decisions
- Testing strategies and coverage
- Domain-specific implementation details

**Default agents are generic.** This tool ships with general-purpose developer agents that work across any project. For significantly better results, we recommend creating **custom agents** with:

- **Domain expertise** (e.g., financial systems, healthcare, e-commerce)
- **Technical specialization** (e.g., API design, database optimization, security)
- **Team conventions** (e.g., your company's coding standards, preferred patterns)

See [Custom Agents](#custom-agents) for how to create and configure phase-specific agents.

## Features

- **Multi-language Support** - Pre-configured profiles for Kotlin, TypeScript, JavaScript, Python, Go, Rust, and Java (with npm/pnpm variants)
- **Auto-detection** - Automatically detects project technology stack
- **Phase Guards** - Prevents editing wrong file types per phase
- **Auto Compile/Test** - Runs compile and test commands automatically
- **User Approval Gates** - Human confirms each phase transition
- **Clean Cleanup** - Session end automatically removes markers

## Quick Start

### Prerequisites

- **Python 3.6+** - Required for hook scripts
- **Bash** - Required for hook execution
- **Claude Code** - The CLI tool this integrates with

### Installation

**Quick install (recommended):**
```bash
curl -fsSL https://raw.githubusercontent.com/PetarMatan/ai-tdd-workflow/main/install.sh | bash
```

**Or clone and install manually:**
```bash
git clone https://github.com/PetarMatan/ai-tdd-workflow.git
cd ai-tdd-workflow
./install.sh
```

**Uninstall:**
```bash
~/.claude/tdd-workflow/uninstall.sh
# Or if you have the repo cloned:
./uninstall.sh
```

### Backup & Recovery

The installer creates a **full backup** of your `~/.claude` directory before making any changes:

```
~/.claude-backup-20250105-143022/
```

If anything goes wrong during or after installation, restore with:
```bash
rm -rf ~/.claude && cp -r ~/.claude-backup-TIMESTAMP ~/.claude
```

The uninstaller also creates a backup of `settings.json` before removing hooks.

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
/tdd-create-agent
```

## Custom Agents

You can create custom agents that auto-load during specific TDD phases. This is useful for domain-specific guidance (e.g., an API design expert for Phase 2, or a testing specialist for Phase 3).

### Creating an Agent

Use `/tdd-create-agent` to interactively create an agent, or manually create a file in `~/.claude/agents/` with YAML frontmatter:

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

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for debugging tips, log locations, and common issues.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Inspired by:
- Robert C. Martin's (Uncle Bob) TDD principles
- Kent Beck's Test-Driven Development methodology
- Claude Code hooks system
