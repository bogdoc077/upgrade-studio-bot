'use client';

import { useState } from 'react';
import { BeakerIcon, UserIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
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
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<{ [key: string]: { success: boolean; message: string } }>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const searchUsers = async (query: string) => {
    if (!query || query.length < 2) {
      setSearchResults([]);
      return;
    }

    setSearching(true);
    try {
      const response = await makeApiCall(`/api/users?search=${encodeURIComponent(query)}&limit=10`, {
        method: 'GET'
      });
      setSearchResults(response.users || []);
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
    setSelectedUserId(user.telegram_id.toString());
    setSearchQuery(`${user.first_name || ''} ${user.last_name || ''} (@${user.username || user.telegram_id})`.trim());
    setSearchResults([]);
  };

  const runTest = async (scenario: TestScenario) => {
    if (!selectedUserId) {
      alert('Будь ласка, оберіть користувача');
      return;
    }

    setLoading(scenario.id);
    try {
      const response = await makeApiCall(scenario.endpoint, {
        method: 'POST',
        body: JSON.stringify({ telegram_id: parseInt(selectedUserId) })
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
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <BeakerIcon style={{ width: '32px', height: '32px', color: '#6366f1' }} />
          <h1 style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>Тестування автоматичних сценаріїв</h1>
        </div>
        <p style={{ color: '#6b7280', fontSize: '14px' }}>
          Запускайте автоматичні сценарії вручну для тестування функціоналу
        </p>
      </div>

      {/* User Selection */}
      <div style={{
        backgroundColor: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <UserIcon style={{ width: '20px', height: '20px', color: '#6b7280' }} />
          <h2 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Вибір користувача</h2>
        </div>

        <div style={{ position: 'relative' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Почніть вводити ім'я, username або Telegram ID..."
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px'
            }}
          />

          {/* Search Results Dropdown */}
          {searchResults.length > 0 && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              marginTop: '4px',
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
              maxHeight: '300px',
              overflowY: 'auto',
              zIndex: 10
            }}>
              {searchResults.map((user) => (
                <div
                  key={user.id}
                  onClick={() => selectUser(user)}
                  style={{
                    padding: '12px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f3f4f6',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f9fafb';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '#fff';
                  }}
                >
                  <div style={{ fontWeight: '500', fontSize: '14px', marginBottom: '4px' }}>
                    {user.first_name} {user.last_name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    @{user.username || user.telegram_id} • ID: {user.telegram_id}
                    {user.subscription_active && (
                      <span style={{
                        marginLeft: '8px',
                        padding: '2px 8px',
                        backgroundColor: '#d1fae5',
                        color: '#065f46',
                        borderRadius: '4px',
                        fontSize: '11px'
                      }}>
                        Активна підписка
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {searching && (
            <div style={{
              position: 'absolute',
              right: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#6b7280'
            }}>
              Пошук...
            </div>
          )}
        </div>

        {selectedUserId && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: '6px',
            fontSize: '14px',
            color: '#166534'
          }}>
            ✓ Обрано користувача з Telegram ID: <strong>{selectedUserId}</strong>
          </div>
        )}
      </div>

      {/* Test Scenarios */}
      <div style={{ display: 'grid', gap: '16px' }}>
        {TEST_SCENARIOS.map((scenario) => {
          const result = results[scenario.id];
          const isLoading = loading === scenario.id;

          return (
            <div
              key={scenario.id}
              style={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '20px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px', margin: 0 }}>
                    {scenario.name}
                  </h3>
                  <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px', margin: 0 }}>
                    {scenario.description}
                  </p>

                  {scenario.requiresActiveSubscription && (
                    <div style={{
                      fontSize: '12px',
                      color: '#92400e',
                      backgroundColor: '#fef3c7',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      display: 'inline-block',
                      marginTop: '8px'
                    }}>
                      ⚠️ Потребує активної підписки
                    </div>
                  )}

                  {scenario.requiresPausedSubscription && (
                    <div style={{
                      fontSize: '12px',
                      color: '#92400e',
                      backgroundColor: '#fef3c7',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      display: 'inline-block',
                      marginTop: '8px'
                    }}>
                      ⚠️ Потребує призупиненої підписки
                    </div>
                  )}

                  {result && (
                    <div style={{
                      marginTop: '12px',
                      padding: '12px',
                      backgroundColor: result.success ? '#f0fdf4' : '#fef2f2',
                      border: `1px solid ${result.success ? '#86efac' : '#fca5a5'}`,
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '8px'
                    }}>
                      {result.success ? (
                        <CheckCircleIcon style={{ width: '20px', height: '20px', color: '#16a34a', flexShrink: 0 }} />
                      ) : (
                        <ExclamationCircleIcon style={{ width: '20px', height: '20px', color: '#dc2626', flexShrink: 0 }} />
                      )}
                      <div style={{
                        fontSize: '14px',
                        color: result.success ? '#166534' : '#991b1b'
                      }}>
                        {result.message}
                      </div>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => runTest(scenario)}
                  disabled={isLoading || !selectedUserId}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: isLoading ? '#9ca3af' : '#6366f1',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: isLoading || !selectedUserId ? 'not-allowed' : 'pointer',
                    opacity: isLoading || !selectedUserId ? 0.6 : 1,
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (!isLoading && selectedUserId) {
                      e.currentTarget.style.backgroundColor = '#4f46e5';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isLoading && selectedUserId) {
                      e.currentTarget.style.backgroundColor = '#6366f1';
                    }
                  }}
                >
                  {isLoading ? 'Виконується...' : 'Запустити тест'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info Block */}
      <div style={{
        marginTop: '24px',
        padding: '16px',
        backgroundColor: '#eff6ff',
        border: '1px solid #bfdbfe',
        borderRadius: '8px'
      }}>
        <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#1e40af', marginBottom: '8px', margin: 0 }}>
          💡 Про тестування
        </h3>
        <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', fontSize: '13px', color: '#1e40af', lineHeight: '1.6' }}>
          <li>Тести надсилають реальні повідомлення обраному користувачу в Telegram</li>
          <li>Деякі тести тимчасово змінюють стан користувача (наприклад, "Закінчення підписки")</li>
          <li>Обирайте тестових користувачів або власний акаунт для перевірки</li>
          <li>Результати тестів відображаються в реальному часі</li>
        </ul>
      </div>
    </div>
  );
}
