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
