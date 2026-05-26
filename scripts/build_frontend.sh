#!/bin/bash
# Build script for the Kairo frontend Svelte application

echo "Building Kairo frontend..."

# Ensure we are in the project root
if [ ! -d "frontend" ]; then
    echo "Error: frontend directory not found. Run this from the project root."
    exit 1
fi

cd frontend || exit 1

echo "Installing npm dependencies..."
npm install --legacy-peer-deps

echo "Compiling static assets..."
npm run build

echo "Frontend build complete! Static files have been placed in app/static/"
