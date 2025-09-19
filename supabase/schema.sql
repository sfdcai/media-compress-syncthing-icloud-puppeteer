-- Supabase Schema for Media Pipeline
CREATE TABLE IF NOT EXISTS media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    status TEXT CHECK (status IN ('downloaded','compressed','batched','uploaded','verified','cleaned')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_type TEXT CHECK (batch_type IN ('iphone','pixel')),
    total_files INT,
    total_size BIGINT,
    status TEXT CHECK (status IN ('pending','uploaded','verified','cleaned')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS pipeline_logs (
    id BIGSERIAL PRIMARY KEY,
    step TEXT,
    message TEXT,
    status TEXT CHECK (status IN ('success','error','warning','info')),
    created_at TIMESTAMP DEFAULT NOW()
);
