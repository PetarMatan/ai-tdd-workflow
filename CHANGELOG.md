# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-03

### Added

- Initial release of TDD Workflow for Claude Code
- Four-phase TDD workflow enforcement:
  - Phase 1: Requirements Gathering
  - Phase 2: Interface Design
  - Phase 3: Test Writing
  - Phase 4: Implementation
- Multi-language support with auto-detection:
  - Kotlin/Maven
  - Kotlin/Gradle
  - TypeScript/npm
  - TypeScript/pnpm
  - JavaScript/npm
  - JavaScript/pnpm
  - Python/pytest
  - Go
  - Rust
  - Java/Maven
- Hook system integration:
  - `tdd-orchestrator.sh` - Stop hook for phase control
  - `tdd-phase-guard.sh` - PreToolUse hook for file type enforcement
  - `tdd-auto-test.sh` - PostToolUse hook for compile+test loop
  - `tdd-auto-compile.sh` - PostToolUse hook for automatic compilation
  - `tdd-cleanup-markers.sh` - SessionEnd hook for state cleanup
- Skill commands:
  - `/tdd` - Activate TDD mode
  - `/tdd-status` - Show current workflow status
  - `/tdd-reset` - Reset TDD state
  - `/tdd-create-agent` - Interactive custom agent generation
- Agent definitions:
  - `tdd-developer.md` - Main TDD workflow guidance
  - `tdd-tester.md` - Test writing expertise
  - `tdd-uncle-bob.md` - Clean code principles
- Custom agent system:
  - Phase-bound agents via YAML frontmatter (`phases: [2, 3]`)
  - Auto-loading of agents when configured phases start
  - `agents.sh` library for agent discovery and loading
- Configuration system:
  - `tdd-config.json` - Technology profiles configuration
  - `schema.json` - JSON Schema for config validation
  - Override support via `~/.claude/tdd-override.json`
- Install/uninstall scripts
- Documentation:
  - README.md with quick start guide
  - Architecture documentation
  - Troubleshooting guide

### Security

- Marker files stored in user's home directory
- No external network requests
- No credential storage
