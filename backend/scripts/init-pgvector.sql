-- Enable pgvector extension for semantic caching
-- This script runs on database initialization

CREATE EXTENSION IF NOT EXISTS vector;
