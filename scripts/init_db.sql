-- Initialize database schema and create extensions

-- Create necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance
-- These will be created automatically by SQLAlchemy but listed here for reference

-- Users table indexes
-- CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
-- CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Documents table indexes
-- CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
-- CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(ingestion_status);
-- CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);
-- CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
-- CREATE INDEX IF NOT EXISTS idx_documents_access_level ON documents(access_level);

-- Chat sessions table indexes
-- CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
-- CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);
-- CREATE INDEX IF NOT EXISTS idx_chat_sessions_is_active ON chat_sessions(is_active);

-- Messages table indexes
-- CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
-- CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
-- CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- Full-text search indexes (optional, for advanced search)
-- CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns (will also be handled by SQLAlchemy)
-- CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();