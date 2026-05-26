#!/bin/bash
# Script to run the Kairo frontend development server

echo "Starting Kairo frontend standalone dev server..."

# Ensure we are in the project root
if [ ! -d "frontend" ]; then
    echo "Error: frontend directory not found. Run this from the project root."
    exit 1
fi

cd frontend || exit 1

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "First time setup: Installing npm dependencies..."
    npm install --legacy-peer-deps
fi

echo "Launching Vite dev server on http://localhost:5173..."
npm run dev
