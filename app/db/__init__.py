# app/db/__init__.py
"""
Database driver override - forces asyncpg instead of psycopg2
"""
import sys
import asyncpg

# Force SQLAlchemy to use asyncpg
from sqlalchemy.dialects.postgresql import asyncpg as asyncpg_dialect

# Ensure asyncpg is loaded before psycopg2
sys.modules['psycopg2'] = None  # Block psycopg2