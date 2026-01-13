# Unit Testing Requirements

## Mandatory Test Coverage
- **ALWAYS** create or modify unit tests when adding or changing code
- When adding new functions, classes, or modules, create corresponding unit tests
- When modifying existing code, update existing tests or add new tests to cover the changes
- When fixing bugs, add tests that reproduce the bug and verify the fix

## Test File Organization
- Place test files in the appropriate `tests/` directory
- Follow the existing test file naming convention (e.g., `test_*.py` for Python)
- Mirror the source code structure in the test directory when possible
- Keep test files close to the code they test, or in a dedicated test directory

## Test Quality Standards
- Write tests that are clear, focused, and test one thing at a time
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases (happy path and error cases)
- Ensure tests are independent and can run in any order
- Mock external dependencies (APIs, databases, file systems, etc.) when appropriate

## Test Execution
- Run tests before committing code changes
- Ensure all tests pass before considering code complete
- Use the appropriate test runner for the project (e.g., `pytest` for Python, `jest` for JavaScript/TypeScript)
- Follow project-specific test execution patterns (e.g., `uv run pytest` for backend Python code)

## Code Changes Without Tests
- If you modify code, you MUST also modify or add tests
- If you add new functionality, you MUST add tests for that functionality
- If you remove functionality, you MUST update or remove related tests
- Never skip test creation or modification - it is a required part of every code change
