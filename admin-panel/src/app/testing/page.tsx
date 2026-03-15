'use client';

import { useState, useEffect, useRef } from 'react';
import { BeakerIcon, UserIcon, CheckCircleIcon, ExclamationCircleIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { makeApiCall } from '@/utils/api-client';

interface TestScenario {
  id: string;
  name: string;
  description: string;
  endpoint: string;
  requiresActiveSubscription?: boolean;
  requiresPausedSubscription?: boolean;
}

const TEST_SCENARIOS: TestScenario[] = [
  {
    id: 'upcoming_payment',
    name: 'Попередження про списання (7 днів)',
    description: 'Надсилає нагадування користувачу, що через 7 днів відбудеться автоматичне списання за підписку.',
    endpoint: '/api/testing/check-upcoming-payment',
    requiresActiveSubscription: true
  },
  {
    id: 'expired_subscription',
    name: 'Закінчення підписки',
    description: 'Імітує закінчення підписки: скидає доступи, надсилає пропозицію оформити підписку знову.',
    endpoint: '/api/testing/expired-subscription'
  },
  {
    id: 'paused_reminder',
    name: 'Нагадування про призупинену підписку',
    description: 'Надсилає нагадування користувачу з призупиненою підпискою про наближення її закінчення.',
    endpoint: '/api/testing/paused-subscription-reminder',
    requiresPausedSubscription: true
  },
  {
    id: 'join_reminder',
    name: 'Нагадування про приєднання',
    description: 'Надсилає нагадування про необхідність приєднатися до каналів та чатів.',
    endpoint: '/api/testing/join-reminder'
  }
];

export default function TestingPage() {
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<{ [key: string]: { success: boolean; message: string } }>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const searchUsers = async (query: string) => {
    if (!query || query.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    setSearching(true);
    setShowDropdown(true);
    try {
      const response = await makeApiCall(`/api/users?search=${encodeURIComponent(query)}&limit=10`, {
        method: 'GET'
      });
      setSearchResults(response.data || []);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    searchUsers(value);
  };

  const selectUser = (user: any) => {
    setSelectedUser(user);
    setSearchQuery(`${user.first_name || ''} ${user.last_name || ''} (@${user.username || user.telegram_id})`.trim());
    setShowDropdown(false);
    setSearchResults([]);
  };

  const runTest = async (scenario: TestScenario) => {
    if (!selectedUser) {
      alert('Будь ласка, оберіть користувача');
      return;
    }

    setLoading(scenario.id);
    try {
      const response = await makeApiCall(scenario.endpoint, {
        method: 'POST',
        body: JSON.stringify({ telegram_id: parseInt(selectedUser.telegram_id) })
      });

      setResults(prev => ({
        ...prev,
        [scenario.id]: { success: true, message: response.message || 'Тест успішно виконано' }
      }));
    } catch (error: any) {
      setResults(prev => ({
        ...prev,
        [scenario.id]: { 
          success: false, 
          message: error.message || error.detail || 'Помилка виконання тесту' 
        }
      }));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <BeakerIcon style={{ width: '32px', height: '32px', color: 'var(--color-primary)' }} />
          <div>
            <h1 className="admin-page__title">Тестування автоматичних сценаріїв</h1>
            <p className="admin-page__subtitle">
              Запускайте автоматичні сценарії вручну для тестування функціоналу
            </p>
          </div>
        </div>
      </div>

      {/* User Selection Card */}
      <div className="admin-card" style={{ marginBottom: '24px' }}>
        <div className="admin-card__header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserIcon style={{ width: '20px', height: '20px', color: 'var(--color-text-secondary)' }} />
            <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>Вибір користувача</h2>
          </div>
        </div>
        
        <div className="admin-card__body">
          <div style={{ position: 'relative' }} ref={dropdownRef}>
            <div style={{ position: 'relative' }}>
              <MagnifyingGlassIcon style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '20px',
                height: '20px',
                color: 'var(--color-text-light)'
              }} />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchChange}
                onFocus={() => searchQuery.length >= 2 && setShowDropdown(true)}
                placeholder="Почніть вводити ім'я, username або Telegram ID..."
                className="admin-form__input"
                style={{ paddingLeft: '42px' }}
              />
              {searching && (
                <div style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)'
                }}>
                  <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                </div>
              )}
            </div>

            {/* Search Results Dropdown */}
            {showDropdown && searchResults.length > 0 && (
              <div style={{
                position: 'absolute',
                zIndex: 10,
                width: '100%',
                marginTop: '4px',
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                boxShadow: 'var(--shadow-lg)',
                maxHeight: '320px',
                overflowY: 'auto'
              }}>
                {searchResults.map((user) => (
                  <div
                    key={user.id}
                    onClick={() => selectUser(user)}
                    style={{
                      padding: '12px 16px',
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--color-border-light)',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--color-gray-50)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, fontSize: '14px', marginBottom: '4px' }}>
                          {user.first_name} {user.last_name}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                          @{user.username || user.telegram_id} • ID: {user.telegram_id}
                        </div>
                      </div>
                      {user.subscription_active && (
                        <span className="admin-badge admin-badge--success" style={{ marginLeft: '12px' }}>
                          Активна
                        </span>
                      )}
                      {user.subscription_paused && (
                        <span className="admin-badge admin-badge--warning" style={{ marginLeft: '12px' }}>
                          Призупинена
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showDropdown && searchQuery.length >= 2 && searchResults.length === 0 && !searching && (
              <div style={{
                position: 'absolute',
                zIndex: 10,
                width: '100%',
                marginTop: '4px',
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                boxShadow: 'var(--shadow-lg)',
                padding: '16px',
                textAlign: 'center',
                fontSize: '14px',
                color: 'var(--color-text-secondary)'
              }}>
                Користувачів не знайдено
              </div>
            )}
          </div>

          {selectedUser && (
            <div className="admin-alert admin-alert--success" style={{ marginTop: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <CheckCircleIcon style={{ width: '20px', height: '20px', flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                    Обрано: {selectedUser.first_name} {selectedUser.last_name}
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.9 }}>
                    Telegram ID: {selectedUser.telegram_id} • @{selectedUser.username || selectedUser.telegram_id}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Test Scenarios */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {TEST_SCENARIOS.map((scenario) => {
          const result = results[scenario.id];
          const isLoading = loading === scenario.id;

          return (
            <div key={scenario.id} className="admin-card">
              <div className="admin-card__body">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '24px' }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>
                      {scenario.name}
                    </h3>
                    <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginBottom: '12px' }}>
                      {scenario.description}
                    </p>

                    {scenario.requiresActiveSubscription && (
                      <span className="admin-badge admin-badge--warning" style={{ fontSize: '12px' }}>
                        ⚠️ Потребує активної підписки
                      </span>
                    )}

                    {scenario.requiresPausedSubscription && (
                      <span className="admin-badge admin-badge--warning" style={{ fontSize: '12px' }}>
                        ⚠️ Потребує призупиненої підписки
                      </span>
                    )}

                    {result && (
                      <div 
                        className={`admin-alert ${result.success ? 'admin-alert--success' : 'admin-alert--danger'}`}
                        style={{ marginTop: '12px' }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                          {result.success ? (
                            <CheckCircleIcon style={{ width: '20px', height: '20px', flexShrink: 0, marginTop: '2px' }} />
                          ) : (
                            <ExclamationCircleIcon style={{ width: '20px', height: '20px', flexShrink: 0, marginTop: '2px' }} />
                          )}
                          <div style={{ fontSize: '14px' }}>
                            {result.message}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => runTest(scenario)}
                    disabled={isLoading || !selectedUser}
                    className="admin-btn admin-btn--primary"
                    style={{ 
                      minWidth: '160px',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {isLoading ? (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                        <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                        Виконується...
                      </span>
                    ) : (
                      'Запустити тест'
                    )}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info Block */}
      <div className="admin-alert admin-alert--info" style={{ marginTop: '24px' }}>
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
            💡 Про тестування
          </h3>
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6' }}>
            <li>Тести надсилають реальні повідомлення обраному користувачу в Telegram</li>
            <li>Деякі тести тимчасово змінюють стан користувача (наприклад, "Закінчення підписки")</li>
            <li>Обирайте тестових користувачів або власний акаунт для перевірки</li>
            <li>Результати тестів відображаються в реальному часі</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
