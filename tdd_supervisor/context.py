#!/usr/bin/env python3
"""
TDD Supervisor - Context Builder

Builds context prompts for each TDD phase, including summaries
from previous phases.
"""

from typing import Optional


class ContextBuilder:
    """Builds context/prompts for each TDD phase."""

    # Summary generation prompts (used at end of each phase)
    REQUIREMENTS_SUMMARY_PROMPT = """
Before we move to the next phase, create a concise requirements summary.

Output ONLY the summary in this exact format (no other text):

# Requirements Summary

## Purpose
[One sentence describing what this feature/component does]

## Functional Requirements
- [Requirement 1]
- [Requirement 2]
- [Add more as needed]

## Edge Cases & Error Handling
- [Edge case 1]
- [Edge case 2]

## Constraints & Decisions
- [Any technical constraints or decisions made]

Keep it concise - this will be passed to the next phase as context.
"""

    INTERFACES_SUMMARY_PROMPT = """
Before we move to testing, list the interfaces you created.

Output ONLY the list in this exact format (no other text):

# Interfaces Created

## Classes/Modules
- `ClassName` - [brief purpose]
- `ClassName2` - [brief purpose]

## Key Methods/Functions
- `methodName(params)` - [brief purpose]
- `methodName2(params)` - [brief purpose]

## Data Types/Models
- `TypeName` - [brief purpose]

Keep it concise - this will be passed to the next phase as context.
"""

    TESTS_SUMMARY_PROMPT = """
Before we move to implementation, list the tests you created.

Output ONLY the list in this exact format (no other text):

# Tests Created

## Test Files
- `test_file.py` (or appropriate extension)

## Test Cases
- `test_case_name` - [what it verifies]
- `test_case_name2` - [what it verifies]

## Coverage Notes
- Happy path: [covered/not covered]
- Edge cases: [list which ones]
- Error scenarios: [list which ones]

Keep it concise - this will be passed to the implementation phase.
"""

    @staticmethod
    def build_phase1_context(user_task: Optional[str] = None) -> str:
        """
        Build context for Phase 1: Requirements Gathering.

        Args:
            user_task: Optional initial task description from user
        """
        task_section = ""
        if user_task:
            task_section = f"""
## Initial Task
The user wants to build:
{user_task}

"""

        return f"""# TDD Workflow - Phase 1: Requirements Gathering

You are in Phase 1 of the TDD workflow. Your goal is to achieve complete,
unambiguous understanding of what needs to be built.
{task_section}
## Your Task
1. Understand what the user wants to build
2. Ask clarifying questions about:
   - Expected behavior and functionality
   - Edge cases and error handling
   - Input/output formats
   - Dependencies and constraints
   - Performance requirements (if relevant)
3. Summarize the requirements back to the user
4. Get explicit confirmation that requirements are complete

## Important
- Do NOT write any code in this phase
- Do NOT design interfaces yet
- Focus entirely on understanding WHAT, not HOW
- When requirements are confirmed, say "PHASE_COMPLETE" to signal you're ready

Begin by asking the user what they want to build (if not already provided).
"""

    @staticmethod
    def build_phase2_context(requirements_summary: str) -> str:
        """
        Build context for Phase 2: Interface Design.

        Args:
            requirements_summary: Summary from Phase 1
        """
        return f"""# TDD Workflow - Phase 2: Interface Design

You are in Phase 2 of the TDD workflow. Your goal is to design the
structural skeleton of the solution WITHOUT implementing business logic.

## Requirements from Phase 1
{requirements_summary}

## Your Task
1. Design class/interface signatures
2. Design method signatures with parameter and return types
3. Create the structural skeleton with:
   - Method stubs that throw NotImplementedError or return TODO markers
   - No actual business logic
4. Ensure the code compiles/type-checks successfully
5. Get user approval on the interface design

## Guidelines
- Focus on the PUBLIC API - what will consumers of this code use?
- Consider separation of concerns
- Use appropriate design patterns if beneficial
- Keep it simple - don't over-engineer

## Important
- Do NOT implement business logic
- Method bodies should be stubs only
- Code MUST compile successfully
- When interfaces are approved, say "PHASE_COMPLETE" to signal you're ready
"""

    @staticmethod
    def build_phase3_context(requirements_summary: str, interfaces_list: str) -> str:
        """
        Build context for Phase 3: Test Writing.

        Args:
            requirements_summary: Summary from Phase 1
            interfaces_list: Interfaces created in Phase 2
        """
        return f"""# TDD Workflow - Phase 3: Test Writing

You are in Phase 3 of the TDD workflow. Your goal is to write tests
that define the expected behavior (Red phase of TDD).

## Requirements from Phase 1
{requirements_summary}

## Interfaces from Phase 2
{interfaces_list}

## Your Task
1. Write unit tests based on the requirements
2. Cover:
   - Happy path scenarios
   - Edge cases identified in requirements
   - Error scenarios and exception handling
   - Boundary conditions
3. Tests should compile but FAIL when run (Red phase)
4. Get user approval on test coverage

## Guidelines
- Each requirement should have at least one test
- Test names should clearly describe what they verify
- Use arrange-act-assert pattern
- Mock external dependencies appropriately

## Important
- Do NOT implement the actual code yet
- Tests MUST compile
- Tests SHOULD fail (they test unimplemented code)
- When tests are approved, say "PHASE_COMPLETE" to signal you're ready
"""

    @staticmethod
    def build_phase4_context(
        requirements_summary: str,
        interfaces_list: str,
        tests_list: str
    ) -> str:
        """
        Build context for Phase 4: Implementation.

        Args:
            requirements_summary: Summary from Phase 1
            interfaces_list: Interfaces created in Phase 2
            tests_list: Tests created in Phase 3
        """
        return f"""# TDD Workflow - Phase 4: Implementation

You are in Phase 4 of the TDD workflow. Your goal is to implement
the business logic to make all tests pass (Green phase of TDD).

## Requirements Summary
{requirements_summary}

## Interfaces Created
{interfaces_list}

## Tests to Pass
{tests_list}

## Your Task
1. Read the test files to understand expected behavior
2. Implement business logic method by method
3. Run tests frequently to verify progress
4. Continue until ALL tests pass

## Guidelines
- The tests are your specification - make them pass
- Implement the simplest solution that passes tests
- If a test seems wrong, discuss with user before changing it
- Refactor for clarity after tests pass (if needed)

## Important
- Focus on making tests pass, not on perfect code
- Run tests after each significant change
- When ALL tests pass, the workflow is complete
"""

    @staticmethod
    def get_summary_prompt(phase: int) -> str:
        """Get the summary generation prompt for a phase."""
        prompts = {
            1: ContextBuilder.REQUIREMENTS_SUMMARY_PROMPT,
            2: ContextBuilder.INTERFACES_SUMMARY_PROMPT,
            3: ContextBuilder.TESTS_SUMMARY_PROMPT,
        }
        return prompts.get(phase, "")
