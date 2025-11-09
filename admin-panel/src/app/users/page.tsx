'use client';

import { useState, useEffect } from 'react';
import { 
  UsersIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/24/outline';

interface User {
  id: number;
  telegram_id: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  is_premium: boolean;
  subscription_end?: string;
  created_at: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/users');
      if (response.ok) {
        const data = await response.json();
        setUsers(data.data || []);
      } else {
        throw new Error('Помилка завантаження користувачів');
      }
    } catch (err) {
      console.error('Error fetching users:', err);
      setError('Помилка завантаження користувачів');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Ви впевнені, що хочете видалити цього користувача?')) {
      return;
    }

    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        await fetchUsers(); // Refresh the list
      } else {
        throw new Error('Помилка видалення користувача');
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      alert('Помилка видалення користувача');
    }
  };

  const filteredUsers = users.filter(user => 
    user.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.first_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.last_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.telegram_id.includes(searchTerm)
  );

  const totalUsers = users.length;
  const premiumUsers = users.filter(u => u.is_premium).length;
  const freeUsers = totalUsers - premiumUsers;

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-flex admin-flex--center" style={{ minHeight: '400px' }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Завантаження користувачів...</p>
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
              onClick={fetchUsers}
              className="admin-btn admin-btn--primary"
            >
              Спробувати знову
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header">
        <h1 className="admin-page__title">Користувачі</h1>
        <p className="admin-page__subtitle">
          Управління користувачами бота та їх підписками
        </p>
        <div className="admin-page__actions">
          <div className="admin-form__group" style={{ marginBottom: 0, minWidth: '200px' }}>
            <input
              type="text"
              placeholder="Пошук користувачів..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="admin-form__input"
            />
          </div>
          <button className="admin-btn admin-btn--primary admin-gap--sm">
            <PlusIcon className="w-4 h-4" />
            Додати користувача
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{totalUsers.toLocaleString()}</div>
                <div className="text-sm text-gray-500">Всього користувачів</div>
              </div>
              <UsersIcon className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{premiumUsers.toLocaleString()}</div>
                <div className="text-sm text-gray-500">Преміум користувачі</div>
              </div>
              <UsersIcon className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{freeUsers.toLocaleString()}</div>
                <div className="text-sm text-gray-500">Безкоштовні</div>
              </div>
              <UsersIcon className="w-8 h-8 text-gray-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="admin-card">
        <div className="admin-card__header">
          <h3 className="admin-card__title">Список користувачів</h3>
          <p className="admin-card__subtitle">
            Знайдено: {filteredUsers.length} з {totalUsers} користувачів
          </p>
        </div>
        <div className="admin-card__body admin-content--no-padding">
          {filteredUsers.length > 0 ? (
            <table className="admin-table">
              <thead className="admin-table__header">
                <tr>
                  <th className="admin-table__header-cell">ID</th>
                  <th className="admin-table__header-cell">Telegram ID</th>
                  <th className="admin-table__header-cell">Username</th>
                  <th className="admin-table__header-cell">Ім'я</th>
                  <th className="admin-table__header-cell">Статус</th>
                  <th className="admin-table__header-cell">Дата реєстрації</th>
                  <th className="admin-table__header-cell">Підписка до</th>
                  <th className="admin-table__header-cell admin-table__header-cell--center">Дії</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="admin-table__row">
                    <td className="admin-table__cell font-medium">{user.id}</td>
                    <td className="admin-table__cell">{user.telegram_id}</td>
                    <td className="admin-table__cell">{user.username || '-'}</td>
                    <td className="admin-table__cell">
                      {`${user.first_name || ''} ${user.last_name || ''}`.trim() || '-'}
                    </td>
                    <td className="admin-table__cell">
                      <span className={`admin-status ${
                        user.is_premium ? 'admin-status--active' : 'admin-status--inactive'
                      }`}>
                        {user.is_premium ? 'Преміум' : 'Безкоштовний'}
                      </span>
                    </td>
                    <td className="admin-table__cell">
                      {new Date(user.created_at).toLocaleDateString('uk-UA')}
                    </td>
                    <td className="admin-table__cell">
                      {user.subscription_end 
                        ? new Date(user.subscription_end).toLocaleDateString('uk-UA')
                        : '-'
                      }
                    </td>
                    <td className="admin-table__cell admin-table__cell--center">
                      <div className="admin-flex admin-gap--sm admin-flex--center">
                        <button 
                          className="admin-btn admin-btn--small admin-btn--secondary"
                          title="Переглянути"
                        >
                          <EyeIcon className="w-4 h-4" />
                        </button>
                        <button 
                          className="admin-btn admin-btn--small admin-btn--secondary"
                          title="Редагувати"
                        >
                          <PencilIcon className="w-4 h-4" />
                        </button>
                        <button 
                          className="admin-btn admin-btn--small admin-btn--danger"
                          title="Видалити"
                          onClick={() => handleDeleteUser(user.id)}
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">
                {searchTerm ? 'Користувачів за запитом не знайдено' : 'Користувачі відсутні'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}