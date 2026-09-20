CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='alerts' AND column_name='assignee_id'
    ) THEN
        ALTER TABLE alerts ADD COLUMN assignee_id INT REFERENCES users(id);
    END IF;
END $$;
