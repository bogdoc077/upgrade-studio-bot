'use client';

import { useState, useEffect } from 'react';
import { 
  Cog6ToothIcon,
  ChatBubbleLeftRightIcon,
  CreditCardIcon,
  ClockIcon,
  GlobeAltIcon,
  CheckCircleIcon,
  XCircleIcon,
  PencilIcon
} from '@heroicons/react/24/outline';

interface BotSettings {
  bot_token: string;
}

interface StripeSettings {
  public_key: string;
  secret_key: string;
  webhook_endpoint: string;
  is_active: boolean;
}

interface SubscriptionSettings {
  monthly_price: number;
  annual_price: number;
  trial_days: number;
  is_active: boolean;
}

interface WebhookSettings {
  url: string;
  secret: string;
  events: string[];
  is_active: boolean;
}

interface Settings {
  bot: BotSettings;
  stripe: StripeSettings;
  subscription: SubscriptionSettings;
  webhook: WebhookSettings;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [tempSettings, setTempSettings] = useState<Partial<Settings>>({});

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/settings');
      if (response.ok) {
        const data = await response.json();
        setSettings(data.data);
      } else {
        throw new Error('Помилка завантаження налаштувань');
      }
    } catch (err) {
      console.error('Error fetching settings:', err);
      setError('Помилка завантаження налаштувань');
    } finally {
      setLoading(false);
    }
  };

  const handleEditSection = (section: string) => {
    if (!settings) return;
    
    setEditingSection(section);
    setTempSettings({
      ...tempSettings,
      [section]: { ...settings[section as keyof Settings] }
    });
  };

  const handleCancelEdit = () => {
    setEditingSection(null);
    setTempSettings({});
  };

  const handleSaveSection = async (section: string) => {
    try {
      const sectionData = tempSettings[section as keyof Settings];
      if (!sectionData) return;

      // Отримуємо токен з localStorage
      const token = localStorage.getItem('auth_token');
      
      const response = await fetch(`/api/settings/${section}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify(sectionData),
      });
      
      if (response.ok) {
        await fetchSettings(); // Refresh settings
        setEditingSection(null);
        setTempSettings({});
      } else {
        throw new Error(`Помилка збереження налаштувань ${section}`);
      }
    } catch (err) {
      console.error(`Error saving ${section} settings:`, err);
      alert(`Помилка збереження налаштувань ${section}`);
    }
  };

  const handleInputChange = (section: string, field: string, value: any) => {
    setTempSettings({
      ...tempSettings,
      [section]: {
        ...tempSettings[section as keyof Settings],
        [field]: value
      }
    });
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-flex admin-flex--center" style={{ minHeight: '400px' }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Завантаження налаштувань...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="admin-flex admin-flex--center" style={{ minHeight: '400px' }}>
          <div className="text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <button 
              onClick={fetchSettings}
              className="admin-btn admin-btn--primary"
            >
              Спробувати знову
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header">
        <h1 className="admin-page__title">Налаштування</h1>
        <p className="admin-page__subtitle">
          Конфігурація системи, інтеграцій та підключених сервісів
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Telegram Bot Settings */}
        <div className="admin-card">
          <div className="admin-card__header">
            <div className="admin-flex admin-flex--between admin-flex--center">
              <div className="admin-flex admin-gap--sm admin-flex--center">
                <ChatBubbleLeftRightIcon className="w-5 h-5 text-blue-500" />
                <h3 className="admin-card__title">Telegram Bot</h3>
              </div>
              <button
                onClick={() => editingSection === 'bot' ? handleCancelEdit() : handleEditSection('bot')}
                className="admin-btn admin-btn--small admin-btn--secondary"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="admin-card__body">
            {editingSection === 'bot' ? (
              <div className="admin-form">
                <div className="admin-form__group">
                  <label className="admin-form__label">Bot Token</label>
                  <input
                    type="text"
                    value={tempSettings.bot?.bot_token || ''}
                    onChange={(e) => handleInputChange('bot', 'bot_token', e.target.value)}
                    className="admin-form__input"
                    placeholder="Введіть токен бота"
                  />
                </div>

                <div className="admin-flex admin-gap--sm">
                  <button
                    onClick={() => handleSaveSection('bot')}
                    className="admin-btn admin-btn--primary admin-btn--small"
                  >
                    Зберегти
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="admin-btn admin-btn--secondary admin-btn--small"
                  >
                    Скасувати
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid gap-4">
                <div>
                  <div className="text-sm text-gray-500">Bot Token</div>
                  <div className="text-sm text-gray-900 font-mono text-xs break-all">
                    {settings.bot.bot_token || 'Не налаштовано'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stripe Settings */}
        <div className="admin-card">
          <div className="admin-card__header">
            <div className="admin-flex admin-flex--between admin-flex--center">
              <div className="admin-flex admin-gap--sm admin-flex--center">
                <CreditCardIcon className="w-5 h-5 text-purple-500" />
                <h3 className="admin-card__title">Stripe</h3>
              </div>
              <button
                onClick={() => editingSection === 'stripe' ? handleCancelEdit() : handleEditSection('stripe')}
                className="admin-btn admin-btn--small admin-btn--secondary"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="admin-card__body">
            {editingSection === 'stripe' ? (
              <div className="admin-form">
                <div className="admin-form__group">
                  <label className="admin-form__label">Public Key</label>
                  <input
                    type="text"
                    value={tempSettings.stripe?.public_key || ''}
                    onChange={(e) => handleInputChange('stripe', 'public_key', e.target.value)}
                    className="admin-form__input"
                    placeholder="pk_..."
                  />
                </div>
                <div className="admin-form__group">
                  <label className="admin-form__label">Secret Key</label>
                  <input
                    type="text"
                    value={tempSettings.stripe?.secret_key || ''}
                    onChange={(e) => handleInputChange('stripe', 'secret_key', e.target.value)}
                    className="admin-form__input"
                    placeholder="sk_..."
                  />
                </div>
                <div className="admin-form__group">
                  <label className="admin-form__label">Webhook secret</label>
                  <input
                    type="text"
                    value={tempSettings.stripe?.webhook_endpoint || ''}
                    onChange={(e) => handleInputChange('stripe', 'webhook_endpoint', e.target.value)}
                    className="admin-form__input"
                    placeholder="whsec_..."
                  />
                </div>

                <div className="admin-flex admin-gap--sm">
                  <button
                    onClick={() => handleSaveSection('stripe')}
                    className="admin-btn admin-btn--primary admin-btn--small"
                  >
                    Зберегти
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="admin-btn admin-btn--secondary admin-btn--small"
                  >
                    Скасувати
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-gray-500">Public Key</div>
                  <div className="text-sm text-gray-900 font-mono text-xs break-all">
                    {settings.stripe.public_key || 'Не налаштовано'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Secret Key</div>
                  <div className="text-sm text-gray-900 font-mono text-xs break-all">
                    {settings.stripe.secret_key || 'Не налаштовано'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Webhook secret</div>
                  <div className="text-sm text-gray-900 font-mono text-xs break-all">
                    {settings.stripe.webhook_endpoint || 'Не налаштовано'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Subscription Settings */}
        <div className="admin-card">
          <div className="admin-card__header">
            <div className="admin-flex admin-flex--between admin-flex--center">
              <div className="admin-flex admin-gap--sm admin-flex--center">
                <ClockIcon className="w-5 h-5 text-green-500" />
                <h3 className="admin-card__title">Підписки</h3>
              </div>
              <button
                onClick={() => editingSection === 'subscription' ? handleCancelEdit() : handleEditSection('subscription')}
                className="admin-btn admin-btn--small admin-btn--secondary"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="admin-card__body">
            {editingSection === 'subscription' ? (
              <div className="admin-form">
                <div className="admin-form__group">
                  <label className="admin-form__label">Вартість підписки (EUR)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={tempSettings.subscription?.monthly_price || 0}
                    onChange={(e) => handleInputChange('subscription', 'monthly_price', parseFloat(e.target.value))}
                    className="admin-form__input"
                    placeholder="9.99"
                  />
                </div>

                <div className="admin-flex admin-gap--sm">
                  <button
                    onClick={() => handleSaveSection('subscription')}
                    className="admin-btn admin-btn--primary admin-btn--small"
                  >
                    Зберегти
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="admin-btn admin-btn--secondary admin-btn--small"
                  >
                    Скасувати
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-gray-500">Вартість підписки</div>
                  <div className="text-sm text-gray-900">
                    €{settings.subscription.monthly_price || 0} EUR
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Webhook Settings */}
        <div className="admin-card">
          <div className="admin-card__header">
            <div className="admin-flex admin-flex--between admin-flex--center">
              <div className="admin-flex admin-gap--sm admin-flex--center">
                <GlobeAltIcon className="w-5 h-5 text-orange-500" />
                <h3 className="admin-card__title">Webhook</h3>
              </div>
              <button
                onClick={() => editingSection === 'webhook' ? handleCancelEdit() : handleEditSection('webhook')}
                className="admin-btn admin-btn--small admin-btn--secondary"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="admin-card__body">
            {editingSection === 'webhook' ? (
              <div className="admin-form">
                <div className="admin-form__group">
                  <label className="admin-form__label">Webhook URL</label>
                  <input
                    type="url"
                    value={tempSettings.webhook?.url || ''}
                    onChange={(e) => handleInputChange('webhook', 'url', e.target.value)}
                    className="admin-form__input"
                    placeholder="https://your-app.com/webhook"
                  />
                </div>


                <div className="admin-flex admin-gap--sm">
                  <button
                    onClick={() => handleSaveSection('webhook')}
                    className="admin-btn admin-btn--primary admin-btn--small"
                  >
                    Зберегти
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="admin-btn admin-btn--secondary admin-btn--small"
                  >
                    Скасувати
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-gray-500">URL</div>
                  <div className="text-sm text-gray-900 break-all">
                    {settings.webhook.url || 'Не налаштовано'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}