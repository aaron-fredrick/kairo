#!/bin/bash
# Migration script to apply database schema evolutions using Alembic

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations successfully applied."
