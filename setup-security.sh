#!/bin/bash
# Setup pre-commit hook for security checks
# Usage: bash setup-security.sh

if [ ! -d .git ]; then
    echo "❌ Not a git repository. Run this from the project root."
    exit 1
fi

echo "🔒 Setting up security checks..."

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy the security check script
cp security_check.py .git/hooks/pre-commit

# Make it executable (Linux/Mac)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    chmod +x .git/hooks/pre-commit
fi

echo "✅ Security checks installed!"
echo ""
echo "🛡️  Pre-commit hook will now check for:"
echo "  - Commits of .env files"
echo "  - Commits of API keys"
echo "  - Commits of passwords"
echo ""
echo "To bypass (NOT RECOMMENDED):"
echo "  git commit --no-verify"
echo ""
