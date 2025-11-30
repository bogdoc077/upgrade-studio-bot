-- Міграція: додати колонку auto_payment_enabled до таблиці users
-- Дата: 2025-11-30

ALTER TABLE users 
ADD COLUMN auto_payment_enabled BOOLEAN DEFAULT TRUE COMMENT 'Статус автоматичного платежу';

-- Встановити значення за замовчуванням для існуючих користувачів
UPDATE users SET auto_payment_enabled = TRUE WHERE auto_payment_enabled IS NULL;
