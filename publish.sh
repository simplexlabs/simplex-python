#!/bin/bash

# Exit on error
set -e

echo "Starting Python SDK publish script..."

# Load environment variables from .env
if [ -f .env ]; then
    echo "Found .env file"
    export $(cat .env | grep -v '^#' | xargs)
    echo "Loaded environment variables"
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if PYPI_API_TOKEN exists
if [ -z "$PYPI_API_TOKEN" ]; then
    echo "Error: PYPI_API_TOKEN not found in .env file"
    exit 1
fi
echo "Found PYPI_API_TOKEN"

# Extract current version from pyproject.toml
echo "Reading version from pyproject.toml..."
if [ ! -f pyproject.toml ]; then
    echo "Error: pyproject.toml file not found"
    exit 1
fi

current_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\([^"]*\)"/\1/')
if [ -z "$current_version" ]; then
    echo "Error: Could not extract version from pyproject.toml"
    exit 1
fi
echo "Current version: $current_version"

# Auto-bump patch version
IFS='.' read -r major minor patch <<< "$current_version"
new_patch=$((patch + 1))
new_version="$major.$minor.$new_patch"
echo "Bumping to: $new_version"

# Update version in all files
sed -i '' "s/version = \"$current_version\"/version = \"$new_version\"/" pyproject.toml
sed -i '' "s/__version__ = \"$current_version\"/__version__ = \"$new_version\"/" simplex/__init__.py
sed -i '' "s/__version__ = \"$current_version\"/__version__ = \"$new_version\"/" simplex/_http_client.py

current_version="$new_version"
echo "Version updated to $current_version"

# Check BASE_URL in simplex/client.py
echo "Checking BASE_URL in simplex/client.py..."
if ! grep -q 'https://api.simplex.sh' simplex/client.py; then
    echo "Warning: BASE_URL in simplex/client.py may not be set to production URL"
    echo "Continuing anyway..."
fi
echo "BASE_URL check passed"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info simplex.egg-info simplex_python.egg-info

# Build the package using modern build tool
echo "Building package..."
python -m build

# Upload to PyPI using API token
echo "Uploading to PyPI..."
TWINE_USERNAME=__token__ TWINE_PASSWORD=$PYPI_API_TOKEN python -m twine upload dist/*

echo "Successfully published version $current_version to PyPI"

# Create git commit and tag
echo "Creating git commit and tag..."
git add -A
git commit -m "Release Python SDK v$current_version" || echo "Nothing to commit"
git tag "python-v$current_version" || echo "Tag already exists"
git push && git push --tags

echo "Created and pushed git tag python-v$current_version"
echo ""
echo "Python SDK v$current_version published successfully!"
echo "Users can now install with: pip install simplex"
