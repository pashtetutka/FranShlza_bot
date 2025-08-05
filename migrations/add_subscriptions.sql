
CREATE TABLE IF NOT EXISTS subscriptions (
    id           SERIAL PRIMARY KEY,                
    user_id      BIGINT      NOT NULL,              
    email        TEXT        NOT NULL,
    status       TEXT        NOT NULL,              
    periodicity  TEXT        NULL,                  
    started_at   DATE        NULL,
    expired_at   DATE        NULL,
    payment_url  TEXT        NOT NULL,
    created_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, payment_url)                   
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status
          ON subscriptions (user_id, status);

ALTER TABLE users ADD COLUMN instagram_nick TEXT;

ALTER TABLE users ADD COLUMN IF NOT EXISTS instagram_nick TEXT;
