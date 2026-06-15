-- Seed auth users (password_hash is SHA-256 hex for demo purposes)
CREATE TABLE IF NOT EXISTS auth_user (
    auth_user_id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ NULL
);

INSERT INTO auth_user (email, password_hash, is_active)
VALUES
  ('demo1@example.com', 'b6cf51c52b8b137ea8fda2add6533110e4aa4dfdf4465f78eb9e7dd14371459d', true),
  ('demo2@example.com', 'e86420fd5858fcf0c560f5f7c50f2fcc3306ae07cfef3371113ba7b5a83a166b', true)
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    is_active = EXCLUDED.is_active;

