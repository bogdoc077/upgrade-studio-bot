'use client';

import { useState, useEffect } from 'react';
import { 
  UsersIcon,
  MagnifyingGlassIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  XCircleIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';
import ViewModal from '@/components/ViewModal';
import DeleteConfirmModal from '@/components/DeleteConfirmModal';
import UserEditModal from '@/components/UserEditModal';
import Pagination from '@/components/Pagination';

interface User {
  id: number;
  telegram_id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  state: string;
  goals?: string;
  injuries?: string;
  subscription_active: number;
  subscription_paused: number;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  joined_channel: number;
  joined_chat: number;
  workouts_completed: number;
  member_since: string;
  created_at: string;
  updated_at: string;
  role: string;
  subscription_cancelled: number;
  subscription_end_date?: string;
  next_billing_date?: string;
  subscription_status: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Filter states
  const [subscriptionStatus, setSubscriptionStatus] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  
  // Modal states
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, [currentPage, itemsPerPage, subscriptionStatus, dateFrom, dateTo]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Отримуємо токен з localStorage або cookie
      const token = localStorage.getItem('auth_token');
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // Формуємо URL з параметрами фільтрації
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: itemsPerPage.toString(),
      });
      
      if (searchTerm) params.append('search', searchTerm);
      if (subscriptionStatus) params.append('subscription_status', subscriptionStatus);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      
      const response = await fetch(`/api/users?${params.toString()}`, {
        headers,
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Users data:', data); // Для діагностики
        setUsers(data.data || []);
        setTotalItems(data.total || 0);
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Помилка завантаження користувачів');
      }
    } catch (err) {
      console.error('Error fetching users:', err);
      setError(err instanceof Error ? err.message : 'Помилка завантаження користувачів');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    try {
      console.log('[Client] Deleting user:', userId);
      setIsDeleting(true);
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log('[Client] Delete response status:', response.status);
      
      if (response.ok) {
        console.log('[Client] Delete successful');
        setShowDeleteModal(false);
        setSelectedUser(null);
        await fetchUsers(); // Refresh the list
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('[Client] Delete failed:', errorData);
        throw new Error(errorData.error || 'Помилка видалення користувача');
      }
    } catch (err) {
      console.error('[Client] Error deleting user:', err);
      alert('Помилка видалення користувача');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleViewUser = (user: User) => {
    setSelectedUser(user);
    setShowViewModal(true);
  };

  const handleDeleteClick = (user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setShowEditModal(true);
  };

  const handleSaveUser = async (userId: number, data: Partial<User>) => {
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        await fetchUsers(); // Refresh the list
      } else {
        throw new Error('Помилка оновлення користувача');
      }
    } catch (err) {
      console.error('Error updating user:', err);
      alert('Помилка оновлення користувача');
      throw err;
    }
  };

  const exportToExcel = async () => {
    try {
      const response = await fetch('/api/users/export', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        throw new Error('Помилка експорту');
      }
    } catch (err) {
      console.error('Error exporting users:', err);
      alert('Помилка експорту користувачів');
    }
  };

  // Фільтрація тепер на сервері через search параметр, тому просто показуємо users
  const filteredUsers = users;

  // Статистика з totalItems (загальна кількість з сервера)
  const totalUsers = totalItems;
  const premiumUsers = users.filter(u => u.subscription_active === 1).length;
  const freeUsers = users.filter(u => u.subscription_active === 0).length;

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading">
          <div className="admin-loading__spinner"></div>
          <p className="admin-loading__text">Завантаження користувачів...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="admin-alert admin-alert--danger">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header admin-page__header--with-actions">
        <div className="admin-page__title-section">
          <h1 className="admin-page__title">Користувачі</h1>
          <p className="admin-page__subtitle">Управління користувачами системи</p>
        </div>
        <button
          onClick={exportToExcel}
          className="admin-btn admin-btn--secondary"
        >
          <ArrowDownTrayIcon className="w-5 h-5" />
          Експорт в Excel
        </button>
      </div>

      {/* Stats Cards */}
      <div className="admin-stats">
        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Всього користувачів</span>
            <UsersIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{totalUsers.toLocaleString()}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Преміум користувачі</span>
            <UsersIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{premiumUsers.toLocaleString()}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Безкоштовні</span>
            <UsersIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{freeUsers.toLocaleString()}</div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="admin-table-container">
        <div className="admin-card__header">
          <h3 className="admin-card__title">Список користувачів</h3>
          <p className="admin-card__subtitle">
            Показано {filteredUsers.length} з {totalUsers} користувачів
          </p>
        </div>
        
        {/* Filters */}
        <div className="admin-filters" style={{ marginBottom: '1.5rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-base)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            {/* Search */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Пошук
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && fetchUsers()}
                  placeholder="Ім'я, username, Telegram ID..."
                  style={{
                    width: '100%',
                    padding: '0.5rem 2.5rem 0.5rem 0.75rem',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.875rem'
                  }}
                />
                <MagnifyingGlassIcon 
                  style={{ 
                    position: 'absolute', 
                    right: '0.75rem', 
                    top: '50%', 
                    transform: 'translateY(-50%)', 
                    width: '1.25rem', 
                    height: '1.25rem',
                    color: 'var(--text-tertiary)',
                    pointerEvents: 'none'
                  }} 
                />
              </div>
            </div>

            {/* Subscription Status Filter */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Статус підписки
              </label>
              <select
                value={subscriptionStatus}
                onChange={(e) => setSubscriptionStatus(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem',
                  background: 'var(--bg-primary)'
                }}
              >
                <option value="">Всі</option>
                <option value="active">Активна</option>
                <option value="inactive">Неактивна</option>
                <option value="paused">Призупинена</option>
                <option value="cancelled">Скасована</option>
              </select>
            </div>

            {/* Date From */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Дата реєстрації від
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem'
                }}
              />
            </div>

            {/* Date To */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Дата реєстрації до
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem'
                }}
              />
            </div>
          </div>

          {/* Filter Actions */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={fetchUsers}
              className="admin-btn admin-btn--primary admin-btn--sm"
            >
              <MagnifyingGlassIcon className="w-4 h-4" />
              Застосувати фільтри
            </button>
            <button
              onClick={() => {
                setSearchTerm('');
                setSubscriptionStatus('');
                setDateFrom('');
                setDateTo('');
                setCurrentPage(1);
              }}
              className="admin-btn admin-btn--secondary admin-btn--sm"
            >
              <XCircleIcon className="w-4 h-4" />
              Очистити
            </button>
          </div>
        </div>

        {filteredUsers.length > 0 ? (
          <>
            <div className="admin-table-wrapper">
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
              <tbody className="admin-table__body">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="admin-table__row">
                    <td className="admin-table__cell admin-table__cell--bold">{user.id}</td>
                    <td className="admin-table__cell">{user.telegram_id.toString()}</td>
                    <td className="admin-table__cell">{user.username || '-'}</td>
                    <td className="admin-table__cell">
                      {`${user.first_name || ''} ${user.last_name || ''}`.trim() || '-'}
                    </td>
                    <td className="admin-table__cell">
                      <span className={`admin-status ${
                        user.subscription_active === 1 ? 'admin-status--active' : 'admin-status--inactive'
                      }`}>
                        {user.subscription_active === 1 ? 'Активна підписка' : 'Неактивний'}
                      </span>
                    </td>
                    <td className="admin-table__cell">
                      {new Date(user.created_at).toLocaleDateString('uk-UA')}
                    </td>
                    <td className="admin-table__cell">
                      {user.subscription_end_date 
                        ? new Date(user.subscription_end_date).toLocaleDateString('uk-UA')
                        : '-'
                      }
                    </td>
                    <td className="admin-table__cell admin-table__cell--center">
                      <div className="flex items-center justify-center gap-2">
                        <button 
                          className="admin-btn admin-btn--sm admin-btn--secondary"
                          title="Переглянути"
                          onClick={() => handleViewUser(user)}
                        >
                          <EyeIcon className="w-4 h-4" />
                        </button>
                        <button 
                          className="admin-btn admin-btn--sm admin-btn--secondary"
                          title="Редагувати"
                          onClick={() => handleEditUser(user)}
                        >
                          <PencilIcon className="w-4 h-4" />
                        </button>
                        <button 
                          className="admin-btn admin-btn--sm admin-btn--danger"
                          title="Видалити"
                          onClick={() => handleDeleteClick(user)}
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          
          {!loading && (
            <Pagination
              currentPage={currentPage}
              totalPages={Math.ceil(totalItems / itemsPerPage)}
              totalItems={totalItems}
              itemsPerPage={itemsPerPage}
              onPageChange={setCurrentPage}
              onItemsPerPageChange={(items) => {
                setItemsPerPage(items);
                setCurrentPage(1);
              }}
            />
          )}
          </>
        ) : (
          <div className="admin-table__empty">
            <UsersIcon className="admin-table__empty-icon" />
            <p className="admin-table__empty-text">
              {searchTerm ? 'Користувачів за запитом не знайдено' : 'Користувачі відсутні'}
            </p>
          </div>
        )}
      </div>

      {/* View Modal */}
      {selectedUser && (
        <ViewModal
          isOpen={showViewModal}
          onClose={() => {
            setShowViewModal(false);
            setSelectedUser(null);
          }}
          title="Деталі користувача"
          fields={[
            { label: 'ID', value: selectedUser.id },
            { label: 'Telegram ID', value: selectedUser.telegram_id },
            { label: 'Username', value: selectedUser.username || '—' },
            { label: "Ім'я", value: `${selectedUser.first_name || ''} ${selectedUser.last_name || ''}`.trim() || '—' },
            { label: 'Статус підписки', value: selectedUser.subscription_active === 1 ? 'Активна' : 'Неактивна', type: 'status' },
            { label: 'Дата реєстрації', value: selectedUser.created_at, type: 'date' },
            { label: 'Підписка до', value: selectedUser.subscription_end_date, type: 'date' },
            { label: 'Наступний платіж', value: selectedUser.next_billing_date, type: 'date' },
            { label: 'Stripe Customer ID', value: selectedUser.stripe_customer_id || '—' },
            { label: 'Тренувань виконано', value: selectedUser.workouts_completed || 0 },
            { label: 'Підписка призупинена', value: selectedUser.subscription_paused === 1, type: 'boolean' },
            { label: 'Цілі', value: selectedUser.goals || '—' },
            { label: 'Травми', value: selectedUser.injuries || '—' },
          ]}
        />
      )}

      {/* Edit Modal */}
      <UserEditModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedUser(null);
        }}
        user={selectedUser}
        onSave={handleSaveUser}
      />

      {/* Delete Confirmation Modal */}
      {selectedUser && (
        <DeleteConfirmModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setSelectedUser(null);
          }}
          onConfirm={() => handleDeleteUser(selectedUser.id)}
          title="Видалити користувача?"
          message="Ця дія незворотна. Всі дані користувача будуть видалені назавжди."
          itemName={`${selectedUser.first_name || ''} ${selectedUser.last_name || ''}`.trim() || `@${selectedUser.username}` || `ID: ${selectedUser.telegram_id}`}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
}