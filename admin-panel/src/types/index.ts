// Типи для навігації
export interface MenuItem {
  id: string;
  label: string;
  path: string;
  icon: string;
}

// Типи для налаштувань
export interface TelegramSettings {
  bot_token: string;
}

export interface StripeSettings {
  stripe_secret_key: string;
  stripe_publishable_key: string;
  stripe_webhook_secret: string;
}

export interface SubscriptionSettings {
  subscription_price: number;
  currency: string;
}

export interface WebhookSettings {
  webhook_url: string;
}

export interface Settings {
  telegram: TelegramSettings;
  stripe: StripeSettings;
  subscription: SubscriptionSettings;
  webhook: WebhookSettings;
}

// Типи для користувачів
export interface User {
  id: number;
  telegram_id: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  is_premium: boolean;
  subscription_end?: string;
  created_at: string;
}

// Типи для платежів
export interface Payment {
  id: number;
  user_id: number;
  telegram_id?: string;
  first_name?: string;
  last_name?: string;
  username?: string;
  amount: number;
  currency: string;
  status: string;
  stripe_payment_intent_id?: string;
  stripe_subscription_id?: string;
  stripe_invoice_id?: string;
  stripe_response_log?: string;  // Повний JSON лог відповіді від Stripe
  created_at: string;
  paid_at?: string;
}

// Типи для адмінів
export interface Admin {
  id: number;
  username: string;
  created_at: string;
  last_login?: string;
  is_active: boolean;
}

// Типи для розсилок (поки заглушка)
export interface Broadcast {
  id: number;
  title: string;
  message: string;
  status: 'draft' | 'sending' | 'sent';
  created_at: string;
  sent_count?: number;
  error_log?: string;
  full_log?: string;
}

// Утиліти
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
}