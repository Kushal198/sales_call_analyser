#!/bin/sh

echo "Running migrations..."
uv run python manage.py migrate --no-input

echo "Seeding sample calls..."
uv run python manage.py seed_calls

echo "Starting server..."
exec uv run python manage.py runserver 0.0.0.0:8000