-- Міграція для виправлення типу колонки telegram_id в таблиці broadcast_queue
-- Проблема: telegram_id має тип INT замість BIGINT, що призводить до overflow
-- для Telegram ID більших за 2147483647

ALTER TABLE broadcast_queue
MODIFY COLUMN telegram_id BIGINT NOT NULL;
