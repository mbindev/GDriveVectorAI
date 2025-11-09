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

-- Create documents table with enhanced tracking and metadata enrichment
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
    -- Metadata enrichment fields
    ai_summary TEXT,
    ai_keywords TEXT[],
    ai_categories TEXT[],
    custom_tags TEXT[],
    language TEXT,
    sentiment_score FLOAT,
    reading_time_minutes INTEGER,
    last_modified_drive TIMESTAMP,
    file_size_bytes BIGINT,
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    enriched_at TIMESTAMP,
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
CREATE INDEX IF NOT EXISTS documents_language_idx ON documents(language);
CREATE INDEX IF NOT EXISTS documents_ai_keywords_idx ON documents USING GIN(ai_keywords);
CREATE INDEX IF NOT EXISTS documents_ai_categories_idx ON documents USING GIN(ai_categories);
CREATE INDEX IF NOT EXISTS documents_custom_tags_idx ON documents USING GIN(custom_tags);

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

-- Create search_history table for analytics
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    query_text TEXT NOT NULL,
    search_type TEXT NOT NULL, -- 'vector', 'metadata', 'chat'
    results_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    filters JSONB, -- store search filters
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create api_usage_logs table for rate limiting
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    api_key TEXT,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create document_versions table
CREATE TABLE IF NOT EXISTS document_versions (
    id SERIAL PRIMARY KEY,
    drive_file_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    file_name TEXT,
    file_size_bytes BIGINT,
    last_modified_drive TIMESTAMP,
    checksum TEXT, -- MD5 or SHA256 hash
    changes_summary TEXT,
    changed_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drive_file_id) REFERENCES documents(drive_file_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (drive_file_id, version_number)
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
CREATE INDEX IF NOT EXISTS search_history_user_id_idx ON search_history(user_id);
CREATE INDEX IF NOT EXISTS search_history_created_at_idx ON search_history(created_at DESC);
CREATE INDEX IF NOT EXISTS search_history_search_type_idx ON search_history(search_type);
CREATE INDEX IF NOT EXISTS api_usage_logs_user_id_idx ON api_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS api_usage_logs_endpoint_idx ON api_usage_logs(endpoint);
CREATE INDEX IF NOT EXISTS api_usage_logs_created_at_idx ON api_usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS document_versions_drive_file_id_idx ON document_versions(drive_file_id);
CREATE INDEX IF NOT EXISTS document_versions_created_at_idx ON document_versions(created_at DESC);

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

-- ============================================================================
-- V3.0.0 SCHEMA ADDITIONS - Brand/Campaign Organization System
-- ============================================================================

-- Create brands table
CREATE TABLE IF NOT EXISTS brands (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    logo_url TEXT,
    brand_color TEXT, -- hex color code for UI
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand_id INTEGER NOT NULL,
    description TEXT,
    campaign_type TEXT, -- holiday, product_launch, seasonal, promotional, etc.
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create clients table
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand_id INTEGER,
    contact_email TEXT,
    contact_phone TEXT,
    company TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create holidays table
CREATE TABLE IF NOT EXISTS holidays (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    holiday_date DATE NOT NULL,
    year INTEGER NOT NULL,
    description TEXT,
    holiday_type TEXT, -- national, religious, commercial, seasonal
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, year)
);

-- Create offers table
CREATE TABLE IF NOT EXISTS offers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand_id INTEGER,
    campaign_id INTEGER,
    offer_type TEXT, -- discount, bundle, bogo, free_shipping, etc.
    description TEXT,
    valid_from DATE,
    valid_to DATE,
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create document_tags junction table for flexible tagging
CREATE TABLE IF NOT EXISTS document_tags (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL,
    tag_type TEXT NOT NULL, -- 'brand', 'campaign', 'client', 'holiday', 'offer'
    tag_id INTEGER NOT NULL,
    tagged_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(drive_file_id) ON DELETE CASCADE,
    FOREIGN KEY (tagged_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (document_id, tag_type, tag_id)
);

-- Add resource_type column to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS resource_type TEXT DEFAULT 'unknown';
-- Types: image, pdf, document, spreadsheet, presentation, video, audio, archive, other

-- Add scan tracking columns to drive_folders
ALTER TABLE drive_folders ADD COLUMN IF NOT EXISTS last_scan_at TIMESTAMP;
ALTER TABLE drive_folders ADD COLUMN IF NOT EXISTS last_scan_status TEXT; -- completed, in_progress, failed
ALTER TABLE drive_folders ADD COLUMN IF NOT EXISTS total_items_count INTEGER DEFAULT 0;
ALTER TABLE drive_folders ADD COLUMN IF NOT EXISTS scanned_items_count INTEGER DEFAULT 0;

-- Create scan_sessions table for tracking scan progress
CREATE TABLE IF NOT EXISTS scan_sessions (
    id SERIAL PRIMARY KEY,
    folder_id TEXT NOT NULL,
    scan_type TEXT NOT NULL, -- 'full', 'incremental', 'manual'
    status TEXT NOT NULL, -- 'pending', 'in_progress', 'completed', 'failed', 'paused'
    total_items INTEGER DEFAULT 0,
    scanned_items INTEGER DEFAULT 0,
    new_items_found INTEGER DEFAULT 0,
    changed_items_found INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    started_by INTEGER,
    FOREIGN KEY (folder_id) REFERENCES drive_folders(folder_id) ON DELETE CASCADE,
    FOREIGN KEY (started_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create scan_progress table for detailed scan tracking
CREATE TABLE IF NOT EXISTS scan_progress (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    item_path TEXT NOT NULL,
    item_type TEXT NOT NULL, -- 'file', 'folder'
    item_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'pending', 'scanned', 'processed', 'failed'
    error_message TEXT,
    file_size_bytes BIGINT,
    processed_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS brands_name_idx ON brands(name);
CREATE INDEX IF NOT EXISTS brands_is_active_idx ON brands(is_active);
CREATE INDEX IF NOT EXISTS campaigns_brand_id_idx ON campaigns(brand_id);
CREATE INDEX IF NOT EXISTS campaigns_start_date_idx ON campaigns(start_date);
CREATE INDEX IF NOT EXISTS campaigns_end_date_idx ON campaigns(end_date);
CREATE INDEX IF NOT EXISTS campaigns_is_active_idx ON campaigns(is_active);
CREATE INDEX IF NOT EXISTS clients_brand_id_idx ON clients(brand_id);
CREATE INDEX IF NOT EXISTS clients_is_active_idx ON clients(is_active);
CREATE INDEX IF NOT EXISTS holidays_date_idx ON holidays(holiday_date);
CREATE INDEX IF NOT EXISTS holidays_year_idx ON holidays(year);
CREATE INDEX IF NOT EXISTS offers_brand_id_idx ON offers(brand_id);
CREATE INDEX IF NOT EXISTS offers_campaign_id_idx ON offers(campaign_id);
CREATE INDEX IF NOT EXISTS offers_valid_from_idx ON offers(valid_from);
CREATE INDEX IF NOT EXISTS offers_valid_to_idx ON offers(valid_to);
CREATE INDEX IF NOT EXISTS document_tags_document_id_idx ON document_tags(document_id);
CREATE INDEX IF NOT EXISTS document_tags_tag_type_idx ON document_tags(tag_type);
CREATE INDEX IF NOT EXISTS document_tags_tag_id_idx ON document_tags(tag_id);
CREATE INDEX IF NOT EXISTS documents_resource_type_idx ON documents(resource_type);
CREATE INDEX IF NOT EXISTS scan_sessions_folder_id_idx ON scan_sessions(folder_id);
CREATE INDEX IF NOT EXISTS scan_sessions_status_idx ON scan_sessions(status);
CREATE INDEX IF NOT EXISTS scan_sessions_started_at_idx ON scan_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS scan_progress_session_id_idx ON scan_progress(session_id);
CREATE INDEX IF NOT EXISTS scan_progress_status_idx ON scan_progress(status);

-- Add triggers for updated_at on new tables
CREATE TRIGGER update_brands_updated_at BEFORE UPDATE ON brands
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON offers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

