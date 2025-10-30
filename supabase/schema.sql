-- Supabase Schema for Media Pipeline

-- Enhanced batches table (must be created first due to foreign key reference)
CREATE TABLE IF NOT EXISTS batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_type TEXT CHECK (batch_type IN ('icloud','pixel')),
    status TEXT CHECK (status IN ('created','uploading','uploaded','verified','error')),
    total_size_gb DECIMAL(10,2),
    file_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Enhanced media_files table
CREATE TABLE IF NOT EXISTS media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_hash TEXT,
    original_size BIGINT,
    compressed_size BIGINT,
    space_saved BIGINT,
    compression_percentage DECIMAL(5,2),
    compression_ratio DECIMAL(5,2),
    is_duplicate BOOLEAN DEFAULT FALSE,
    source_path TEXT,
    status TEXT CHECK (status IN ('downloaded','deduplicated','compressed','batched','uploaded','verified','error')),
    batch_id UUID REFERENCES batches(id),
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Duplicate files tracking
CREATE TABLE IF NOT EXISTS duplicate_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_file_id UUID REFERENCES media_files(id),
    duplicate_file_id UUID REFERENCES media_files(id),
    hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pipeline logs (matches utils.py)
CREATE TABLE IF NOT EXISTS pipeline_logs (
    id BIGSERIAL PRIMARY KEY,
    step TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT CHECK (status IN ('info','success','error','warning')),
    created_at TIMESTAMP DEFAULT NOW()
);


-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_media_files_hash ON media_files(file_hash);
CREATE INDEX IF NOT EXISTS idx_media_files_status ON media_files(status);
CREATE INDEX IF NOT EXISTS idx_media_files_batch_id ON media_files(batch_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_files_hash ON duplicate_files(hash);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_step ON pipeline_logs(step);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_status ON pipeline_logs(status);
