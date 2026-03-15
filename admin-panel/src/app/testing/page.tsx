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

  // Close dropdown when clicking outside
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

  const getStatusBadgeColor = (status: string) => {
    if (status === 'active') return 'bg-green-100 text-green-800';
    if (status === 'paused') return 'bg-yellow-100 text-yellow-800';
    if (status === 'cancelled') return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <BeakerIcon className="w-8 h-8 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Тестування автоматичних сценаріїв</h1>
        </div>
        <p className="text-gray-600 text-sm">
          Запускайте автоматичні сценарії вручну для тестування функціоналу
        </p>
      </div>

      {/* User Selection */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <UserIcon className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">Вибір користувача</h2>
        </div>

        <div className="relative" ref={dropdownRef}>
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => searchQuery.length >= 2 && setShowDropdown(true)}
              placeholder="Почніть вводити ім'я, username або Telegram ID..."
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
            />
            {searching && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
              </div>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
              {searchResults.map((user) => (
                <div
                  key={user.id}
                  onClick={() => selectUser(user)}
                  className="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 text-sm">
                        {user.first_name} {user.last_name}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        @{user.username || user.telegram_id} • ID: {user.telegram_id}
                      </div>
                    </div>
                    {user.subscription_active && (
                      <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor('active')}`}>
                        Активна
                      </span>
                    )}
                    {user.subscription_paused && (
                      <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor('paused')}`}>
                        Призупинена
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {showDropdown && searchQuery.length >= 2 && searchResults.length === 0 && !searching && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4 text-center text-sm text-gray-500">
              Користувачів не знайдено
            </div>
          )}
        </div>

        {selectedUser && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
            <CheckCircleIcon className="w-5 h-5 text-green-600 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-sm font-medium text-green-900">
                Обрано: {selectedUser.first_name} {selectedUser.last_name}
              </div>
              <div className="text-xs text-green-700">
                Telegram ID: {selectedUser.telegram_id} • @{selectedUser.username || selectedUser.telegram_id}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Test Scenarios */}
      <div className="space-y-4">
        {TEST_SCENARIOS.map((scenario) => {
          const result = results[scenario.id];
          const isLoading = loading === scenario.id;

          return (
            <div
              key={scenario.id}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-gray-900 mb-2">
                    {scenario.name}
                  </h3>
                  <p className="text-sm text-gray-600 mb-3">
                    {scenario.description}
                  </p>

                  {scenario.requiresActiveSubscription && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                      ⚠️ Потребує активної підписки
                    </span>
                  )}

                  {scenario.requiresPausedSubscription && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                      ⚠️ Потребує призупиненої підписки
                    </span>
                  )}

                  {result && (
                    <div className={`mt-3 p-3 rounded-lg flex items-start gap-2 ${
                      result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                    }`}>
                      {result.success ? (
                        <CheckCircleIcon className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <ExclamationCircleIcon className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div className={`text-sm ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                        {result.message}
                      </div>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => runTest(scenario)}
                  disabled={isLoading || !selectedUser}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                    isLoading || !selectedUser
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800'
                  }`}
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Виконується...
                    </span>
                  ) : (
                    'Запустити тест'
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info Block */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">
          💡 Про тестування
        </h3>
        <ul className="space-y-1 text-sm text-blue-800">
          <li>• Тести надсилають реальні повідомлення обраному користувачу в Telegram</li>
          <li>• Деякі тести тимчасово змінюють стан користувача (наприклад, "Закінчення підписки")</li>
          <li>• Обирайте тестових користувачів або власний акаунт для перевірки</li>
          <li>• Результати тестів відображаються в реальному часі</li>
        </ul>
      </div>
    </div>
  );
}
