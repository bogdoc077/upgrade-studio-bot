-- Додати поле email до таблиці users для зберігання Stripe email
ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL AFTER stripe_subscription_id;

-- Додати індекс для швидкого пошуку по email
CREATE INDEX idx_users_email ON users(email);
