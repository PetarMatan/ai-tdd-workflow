#!/bin/bash
# Test runner for TDD Workflow
# Usage: ./tests/run_tests.sh [options]
#
# Options:
#   -u, --unit        Run only unit tests
#   -h, --hooks       Run only hook tests
#   -i, --integration Run only integration tests
#   -v, --verbose     Verbose output
#   --filter PATTERN  Run tests matching pattern

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default options
RUN_UNIT=true
RUN_HOOKS=true
RUN_INTEGRATION=true
VERBOSE=""
FILTER=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            RUN_UNIT=true
            RUN_HOOKS=false
            RUN_INTEGRATION=false
            shift
            ;;
        -h|--hooks)
            RUN_UNIT=false
            RUN_HOOKS=true
            RUN_INTEGRATION=false
            shift
            ;;
        -i|--integration)
            RUN_UNIT=false
            RUN_HOOKS=false
            RUN_INTEGRATION=true
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose-run"
            shift
            ;;
        --filter)
            FILTER="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -u, --unit        Run only unit tests"
            echo "  -h, --hooks       Run only hook tests"
            echo "  -i, --integration Run only integration tests"
            echo "  -v, --verbose     Verbose output"
            echo "  --filter PATTERN  Run tests matching pattern"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for bats
if ! command -v bats &> /dev/null; then
    echo "Error: bats is not installed."
    echo ""
    echo "Install with:"
    echo "  brew install bats-core    # macOS"
    echo "  apt install bats          # Debian/Ubuntu"
    echo "  npm install -g bats       # npm"
    exit 1
fi

# Print header
echo "========================================"
echo "  TDD Workflow Test Suite"
echo "========================================"
echo ""

# Collect test files
TEST_FILES=()

if [[ "$RUN_UNIT" == "true" ]]; then
    for f in "$SCRIPT_DIR"/unit/*.bats; do
        [[ -f "$f" ]] && TEST_FILES+=("$f")
    done
fi

if [[ "$RUN_HOOKS" == "true" ]]; then
    for f in "$SCRIPT_DIR"/hooks/*.bats; do
        [[ -f "$f" ]] && TEST_FILES+=("$f")
    done
fi

if [[ "$RUN_INTEGRATION" == "true" ]]; then
    for f in "$SCRIPT_DIR"/integration/*.bats; do
        [[ -f "$f" ]] && TEST_FILES+=("$f")
    done
fi

# Apply filter if specified
if [[ -n "$FILTER" ]]; then
    FILTERED=()
    for f in "${TEST_FILES[@]}"; do
        if [[ "$f" == *"$FILTER"* ]]; then
            FILTERED+=("$f")
        fi
    done
    TEST_FILES=("${FILTERED[@]}")
fi

if [[ ${#TEST_FILES[@]} -eq 0 ]]; then
    echo "No test files found!"
    exit 1
fi

echo "Running ${#TEST_FILES[@]} test file(s)..."
echo ""

# Run tests
BATS_OPTS="--timing"
if [[ -n "$VERBOSE" ]]; then
    BATS_OPTS="$BATS_OPTS $VERBOSE"
fi

bats $BATS_OPTS "${TEST_FILES[@]}"

echo ""
echo "========================================"
echo "  All tests passed!"
echo "========================================"
