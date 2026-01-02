# Troubleshooting Guide

## Common Issues

### TDD Mode Not Activating

**Symptoms:**
- `/tdd` command doesn't activate TDD mode
- Phase guards not working

**Solutions:**

1. Check marker directory exists:
   ```bash
   mkdir -p ~/.claude/tmp
   ```

2. Verify markers can be created:
   ```bash
   touch ~/.claude/tmp/test && rm ~/.claude/tmp/test
   echo "Success"
   ```

3. Check permissions on settings.json allow marker operations:
   ```json
   "permissions": {
     "allow": [
       "Bash(mkdir -p ~/.claude/tmp:*)",
       "Bash(touch ~/.claude/tmp/:*)"
     ]
   }
   ```

### Hooks Not Running

**Symptoms:**
- No compilation after file changes
- Phase transitions not happening
- No blocking messages

**Solutions:**

1. Verify installation:
   ```bash
   ls -la ~/.claude/tdd-workflow/hooks/
   ```

2. Check hooks are executable:
   ```bash
   chmod +x ~/.claude/tdd-workflow/hooks/*.sh
   ```

3. Verify settings.json has hooks configured:
   ```bash
   cat ~/.claude/settings.json | grep -A5 "tdd-orchestrator"
   ```

4. Check for syntax errors in hooks:
   ```bash
   bash -n ~/.claude/tdd-workflow/hooks/tdd-orchestrator.sh
   ```

### Wrong Profile Detected

**Symptoms:**
- Compile command for wrong language
- Source patterns not matching files

**Solutions:**

1. Check detected profile:
   ```bash
   # In project directory
   cat ~/.claude/tdd-workflow/config/tdd-config.json | python3 -c "
   import json, sys
   config = json.load(sys.stdin)
   for name, profile in config['profiles'].items():
       print(f'{name}: {profile[\"detection\"]}')"
   ```

2. Force a specific profile:
   ```bash
   echo '{"activeProfile": "typescript-npm"}' > ~/.claude/tdd-override.json
   ```

3. Clear override:
   ```bash
   rm ~/.claude/tdd-override.json
   ```

### Stuck in a Phase

**Symptoms:**
- Can't advance to next phase
- Marker file not being created

**Solutions:**

1. Check current status:
   ```bash
   /tdd-status
   ```

2. Check if marker file exists:
   ```bash
   ls -la ~/.claude/tmp/tdd-*
   ```

3. Manually create marker (if appropriate):
   ```bash
   touch ~/.claude/tmp/tdd-requirements-confirmed  # Phase 1->2
   touch ~/.claude/tmp/tdd-interfaces-designed     # Phase 2->3
   touch ~/.claude/tmp/tdd-tests-approved          # Phase 3->4
   ```

4. Reset and start over:
   ```bash
   /tdd-reset
   ```

### Compilation Errors Not Displayed

**Symptoms:**
- Build fails but no errors shown
- Generic "compilation failed" message

**Solutions:**

1. Check compile output file:
   ```bash
   cat /tmp/compile-output.txt
   ```

2. Run compile command manually (based on your stack):
   ```bash
   # Maven (Kotlin/Java)
   mvn clean compile

   # Gradle (Kotlin/Java)
   ./gradlew compileKotlin

   # TypeScript/npm
   npm run build

   # Python
   python -m py_compile src/main.py

   # Go
   go build ./...

   # Rust
   cargo build
   ```

3. Check if Python 3 is available:
   ```bash
   python3 --version
   ```

### Tests Not Running in Phase 4

**Symptoms:**
- Compile works but tests don't run
- Test results not showing

**Solutions:**

1. Check test output file:
   ```bash
   cat /tmp/tdd-test-output.txt
   ```

2. Run test command manually (based on your stack):
   ```bash
   # Maven (Kotlin/Java)
   mvn test

   # Gradle (Kotlin/Java)
   ./gradlew test

   # TypeScript/npm
   npm test

   # Python/pytest
   python -m pytest

   # Go
   go test ./...

   # Rust
   cargo test
   ```

3. Verify TDD phase is 4:
   ```bash
   cat ~/.claude/tmp/tdd-phase
   ```

## Log Analysis

### View Recent Logs

```bash
# View current session log
cat ~/.claude/logs/current.log

# View today's log
cat ~/.claude/logs/$(date +%Y-%m-%d).log

# Search for TDD events
grep "\[TDD\]" ~/.claude/logs/current.log
```

### Common Log Patterns

**Successful phase transition:**
```
[2025-01-02 10:30:15] [TDD] Phase 1 -> 2: Requirements confirmed, advancing to Interfaces
```

**Blocked operation:**
```
[2025-01-02 10:30:20] [TDD] Phase 1: Blocked - requirements not confirmed
```

**Build failure:**
```
[2025-01-02 10:30:25] [BUILD] FAILED - Compilation errors in src/main/Service.java
```

## Reinstallation

If all else fails, reinstall:

```bash
# Uninstall
cd /path/to/tdd-workflow-claude
./uninstall.sh

# Clean up any remaining files
rm -rf ~/.claude/tdd-workflow
rm -f ~/.claude/tmp/tdd-*

# Reinstall
./install.sh
```

## Getting Help

1. Check the [README](../README.md) for basic usage
2. Review [Architecture](architecture.md) for system design
3. Open an issue on GitHub with:
   - Your OS and Claude Code version
   - Contents of `~/.claude/logs/current.log`
   - Output of `ls -la ~/.claude/tdd-workflow/`
   - Your `~/.claude/settings.json` (redact sensitive info)
