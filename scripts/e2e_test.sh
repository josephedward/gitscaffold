#!/bin/bash

set -e # Exit on first error

# 1. Setup
echo "Setting up test environment..."
mkdir -p temp_e2e_test

# 2. Create sample codebase and issue
echo "Creating sample files..."
echo 'def add(a, b):
    return a - b # Bug here' > temp_e2e_test/calculator.py

echo 'The add function in calculator.py is incorrect. It should perform addition, not subtraction.' > temp_e2e_test/issues.txt

# 3. Initialize Git
echo "Initializing git repository..."
git -C temp_e2e_test init
git -C temp_e2e_test config --global user.email "test@example.com"
git -C temp_e2e_test config --global user.name "Test User"
git -C temp_e2e_test add .
git -C temp_e2e_test commit -m "Initial commit"

# 4. Run the agent
echo "Running the Gemini agent..."
/Users/user/Documents/GitHub/gitscaffold/venv/bin/python -m scaffold.cli process-issues temp_e2e_test/issues.txt --agent gemini

# 5. Verify the results
echo "Verifying results..."

# Check file content
if ! grep -q "return a + b" temp_e2e_test/calculator.py; then
    echo "TEST FAILED: calculator.py was not fixed correctly."
    exit 1
fi

# Check git commit
if ! git -C temp_e2e_test log -1 | grep -q "fix: The add function in calculator.py is incorrect. It should perform addition, not subtraction."; then
    echo "TEST FAILED: The git commit message is incorrect."
    exit 1
fi

echo "✅ End-to-end test passed!"

# 6. Cleanup
# rm -rf temp_e2e_test

echo "--- Content of temp_e2e_test/calculator.py ---"
cat temp_e2e_test/calculator.py

echo "--- Git log from temp_e2e_test ---"
git -C temp_e2e_test log -1 --pretty=format:%B
