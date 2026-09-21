-- =============================================
-- Phase 6: Rules Engine, XAI, Collaboration
-- =============================================

-- 1. Rules table for Dynamic Rule Engine
CREATE TABLE IF NOT EXISTS rules (
    rule_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    threshold NUMERIC NOT NULL DEFAULT 10000,
    window_seconds INT NOT NULL DEFAULT 60,
    max_count INT DEFAULT 3,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default rules
INSERT INTO rules (name, description, threshold, window_seconds, max_count, is_active) VALUES
    ('HIGH_VELOCITY', 'Phát hiện giao dịch vượt ngưỡng giá trị trong khoảng thời gian ngắn', 10000, 60, 1, TRUE),
    ('STRUCTURING_SUSPICION', 'Phát hiện hành vi chia nhỏ giao dịch để tránh ngưỡng báo cáo (Smurfing)', 9000, 3600, 5, TRUE),
    ('CIRCULAR_TRANSFER', 'Phát hiện chuỗi giao dịch vòng tròn giữa các tài khoản', 5000, 300, 3, TRUE)
ON CONFLICT (name) DO NOTHING;

-- 2. Add XAI explanation column to alerts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='alerts' AND column_name='xai_explanation'
    ) THEN
        ALTER TABLE alerts ADD COLUMN xai_explanation TEXT;
    END IF;
END $$;

-- 3. Add notes column to alerts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='alerts' AND column_name='notes'
    ) THEN
        ALTER TABLE alerts ADD COLUMN notes TEXT;
    END IF;
END $$;

-- 4. Add evidence_file_url column to alerts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='alerts' AND column_name='evidence_file_url'
    ) THEN
        ALTER TABLE alerts ADD COLUMN evidence_file_url VARCHAR(500);
    END IF;
END $$;
