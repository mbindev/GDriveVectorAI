-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create drive_folders table for multi-folder management
CREATE TABLE IF NOT EXISTS drive_folders (
    id SERIAL PRIMARY KEY,
    folder_id TEXT UNIQUE NOT NULL,
    folder_name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create ingestion_jobs table for job tracking
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id SERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    folder_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES drive_folders(folder_id) ON DELETE SET NULL
);

-- Create documents table with enhanced tracking
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    drive_file_id TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    drive_url TEXT,
    folder_id TEXT,
    extracted_text_snippet TEXT,
    full_text_length INTEGER,
    embedding VECTOR(768),
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES drive_folders(folder_id) ON DELETE SET NULL,
    FOREIGN KEY (job_id) REFERENCES ingestion_jobs(job_id) ON DELETE SET NULL
);

-- Create processing_logs table for detailed error tracking
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    drive_file_id TEXT NOT NULL,
    job_id TEXT,
    log_level TEXT NOT NULL, -- info, warning, error
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drive_file_id) REFERENCES documents(drive_file_id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES ingestion_jobs(job_id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS documents_folder_id_idx ON documents(folder_id);
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);
CREATE INDEX IF NOT EXISTS documents_job_id_idx ON documents(job_id);
CREATE INDEX IF NOT EXISTS documents_created_at_idx ON documents(created_at DESC);

CREATE INDEX IF NOT EXISTS ingestion_jobs_status_idx ON ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS ingestion_jobs_folder_id_idx ON ingestion_jobs(folder_id);
CREATE INDEX IF NOT EXISTS ingestion_jobs_started_at_idx ON ingestion_jobs(started_at DESC);

CREATE INDEX IF NOT EXISTS processing_logs_job_id_idx ON processing_logs(job_id);
CREATE INDEX IF NOT EXISTS processing_logs_drive_file_id_idx ON processing_logs(drive_file_id);
CREATE INDEX IF NOT EXISTS processing_logs_created_at_idx ON processing_logs(created_at DESC);

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    api_key TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create sessions table for JWT refresh tokens
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    refresh_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    type TEXT NOT NULL, -- email, webhook, in_app
    category TEXT NOT NULL, -- job_completed, job_failed, document_processed, document_failed
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    is_read BOOLEAN DEFAULT false,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create scheduled_jobs table for automated tasks
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id SERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    job_type TEXT NOT NULL, -- sync_folder, cleanup_old_docs, backup
    folder_id TEXT,
    schedule_cron TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    run_count INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES drive_folders(folder_id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create webhook_configs table
CREATE TABLE IF NOT EXISTS webhook_configs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    events TEXT[] NOT NULL, -- array of event types to trigger on
    is_active BOOLEAN DEFAULT true,
    secret_key TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Add user_id to existing tables
ALTER TABLE drive_folders ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);
CREATE INDEX IF NOT EXISTS users_username_idx ON users(username);
CREATE INDEX IF NOT EXISTS users_api_key_idx ON users(api_key);
CREATE INDEX IF NOT EXISTS user_sessions_user_id_idx ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS user_sessions_refresh_token_idx ON user_sessions(refresh_token);
CREATE INDEX IF NOT EXISTS notifications_user_id_idx ON notifications(user_id);
CREATE INDEX IF NOT EXISTS notifications_is_read_idx ON notifications(is_read);
CREATE INDEX IF NOT EXISTS notifications_created_at_idx ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS scheduled_jobs_next_run_idx ON scheduled_jobs(next_run);
CREATE INDEX IF NOT EXISTS scheduled_jobs_is_active_idx ON scheduled_jobs(is_active);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_drive_folders_updated_at BEFORE UPDATE ON drive_folders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_configs_updated_at BEFORE UPDATE ON webhook_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123 - CHANGE THIS!)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (username, email, password_hash, full_name, is_admin, is_active)
VALUES ('admin', 'admin@drivevectorai.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLSKeera', 'System Administrator', true, true)
ON CONFLICT (username) DO NOTHING;
