'use client';

import { useState, useEffect } from 'react';
import { 
  UserGroupIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  ShieldCheckIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

interface Admin {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  is_superadmin: boolean;
  can_manage_users: boolean;
  can_manage_payments: boolean;
  can_manage_settings: boolean;
  can_manage_admins: boolean;
  created_at: string;
  last_login_at?: string;
}

export default function AdminsPage() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAdminData, setNewAdminData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    role: 'admin',
    can_manage_users: true,
    can_manage_payments: true,
    can_manage_settings: false,
    can_manage_admins: false
  });

  useEffect(() => {
    fetchAdmins();
  }, []);

  const fetchAdmins = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/admins');
      if (response.ok) {
        const data = await response.json();
        setAdmins(data.data || []);
      } else {
        throw new Error('Помилка завантаження адміністраторів');
      }
    } catch (err) {
      console.error('Error fetching admins:', err);
      setError('Помилка завантаження адміністраторів');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAdmin = async () => {
    // Валідація
    if (!newAdminData.username.trim()) {
      alert('Введіть username адміністратора');
      return;
    }
    if (!newAdminData.email.trim()) {
      alert('Введіть email адміністратора');
      return;
    }
    if (!newAdminData.first_name.trim()) {
      alert('Введіть ім\'я адміністратора');
      return;
    }
    if (!newAdminData.password.trim()) {
      alert('Введіть пароль адміністратора');
      return;
    }

    try {
      const response = await fetch('/api/admins', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newAdminData),
      });
      
      if (response.ok) {
        setNewAdminData({
          username: '',
          email: '',
          first_name: '',
          last_name: '',
          password: '',
          role: 'admin',
          can_manage_users: true,
          can_manage_payments: true,
          can_manage_settings: false,
          can_manage_admins: false
        });
        setShowCreateModal(false);
        await fetchAdmins(); // Refresh the list
      } else {
        const errorData = await response.json();
        throw new Error(errorData.message || errorData.detail || 'Помилка створення адміністратора');
      }
    } catch (err) {
      console.error('Error creating admin:', err);
      alert(`Помилка створення адміністратора: ${err}`);
    }
  };

  const handleToggleAdmin = async (adminId: number, currentStatus: boolean) => {
    try {
      const response = await fetch(`/api/admins/${adminId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !currentStatus }),
      });
      
      if (response.ok) {
        await fetchAdmins(); // Refresh the list
      } else {
        throw new Error('Помилка зміни статусу адміністратора');
      }
    } catch (err) {
      console.error('Error toggling admin:', err);
      alert('Помилка зміни статусу адміністратора');
    }
  };

  const handleDeleteAdmin = async (adminId: number, username: string) => {
    if (!confirm(`Ви впевнені, що хочете видалити адміністратора "${username}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/admins/${adminId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        await fetchAdmins(); // Refresh the list
      } else {
        throw new Error('Помилка видалення адміністратора');
      }
    } catch (err) {
      console.error('Error deleting admin:', err);
      alert('Помилка видалення адміністратора');
    }
  };

  const filteredAdmins = admins.filter(admin => 
    admin.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalAdmins = admins.length;
  const activeAdmins = admins.filter(a => a.is_active).length;
  const inactiveAdmins = totalAdmins - activeAdmins;

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Ніколи';
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 60) {
      return `${diffInMinutes} хв тому`;
    } else if (diffInMinutes < 1440) {
      return `${Math.floor(diffInMinutes / 60)} год тому`;
    } else if (diffInMinutes < 43200) { // 30 days
      return `${Math.floor(diffInMinutes / 1440)} дн тому`;
    } else {
      return date.toLocaleDateString('uk-UA');
    }
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-flex admin-flex--center" style={{ minHeight: '400px' }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Завантаження адміністраторів...</p>
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
              onClick={fetchAdmins}
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
        <h1 className="admin-page__title">Адміністратори</h1>
        <p className="admin-page__subtitle">
          Управління адміністраторами системи та їх правами доступу
        </p>
        <div className="admin-page__actions">
          <div className="admin-form__group" style={{ marginBottom: 0, minWidth: '200px' }}>
            <input
              type="text"
              placeholder="Пошук адміністраторів..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="admin-form__input"
            />
          </div>
          <button 
            className="admin-btn admin-btn--primary admin-gap--sm"
            onClick={() => setShowCreateModal(true)}
          >
            <PlusIcon className="w-4 h-4" />
            Додати адміністратора
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{totalAdmins}</div>
                <div className="text-sm text-gray-500">Всього адмінів</div>
              </div>
              <UserGroupIcon className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{activeAdmins}</div>
                <div className="text-sm text-gray-500">Активні</div>
              </div>
              <ShieldCheckIcon className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{inactiveAdmins}</div>
                <div className="text-sm text-gray-500">Неактивні</div>
              </div>
              <ClockIcon className="w-8 h-8 text-yellow-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Admins Table */}
      <div className="admin-card">
        <div className="admin-card__header">
          <h3 className="admin-card__title">Список адміністраторів</h3>
          <p className="admin-card__subtitle">
            Знайдено: {filteredAdmins.length} з {totalAdmins} адміністраторів
          </p>
        </div>
        <div className="admin-card__body admin-content--no-padding">
          {filteredAdmins.length > 0 ? (
            <table className="admin-table">
              <thead className="admin-table__header">
                <tr>
                  <th className="admin-table__header-cell">ID</th>
                  <th className="admin-table__header-cell">Ім'я</th>
                  <th className="admin-table__header-cell">Username</th>
                  <th className="admin-table__header-cell">Email</th>
                  <th className="admin-table__header-cell">Роль</th>
                  <th className="admin-table__header-cell">Права</th>
                  <th className="admin-table__header-cell">Статус</th>
                  <th className="admin-table__header-cell">Останній вхід</th>
                  <th className="admin-table__header-cell admin-table__header-cell--center">Дії</th>
                </tr>
              </thead>
              <tbody>
                {filteredAdmins.map((admin) => (
                  <tr key={admin.id} className="admin-table__row">
                    <td className="admin-table__cell font-medium">{admin.id}</td>
                    <td className="admin-table__cell">
                      <div className="admin-table__user-info">
                        <div className="admin-table__user-name">
                          {admin.first_name} {admin.last_name || ''}
                        </div>
                        {admin.is_superadmin && (
                          <div className="admin-table__user-badge">
                            <ShieldCheckIcon className="w-3 h-3" />
                            Super Admin
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="admin-table__cell font-medium">{admin.username}</td>
                    <td className="admin-table__cell">{admin.email}</td>
                    <td className="admin-table__cell">
                      <span className="admin-role-badge admin-role-badge--admin">
                        {admin.role}
                      </span>
                    </td>
                    <td className="admin-table__cell">
                      <div className="admin-permissions">
                        {admin.can_manage_users && <span className="admin-permission-tag">Users</span>}
                        {admin.can_manage_payments && <span className="admin-permission-tag">Payments</span>}
                        {admin.can_manage_settings && <span className="admin-permission-tag">Settings</span>}
                        {admin.can_manage_admins && <span className="admin-permission-tag">Admins</span>}
                      </div>
                    </td>
                    <td className="admin-table__cell">
                      <span className={`admin-status ${
                        admin.is_active ? 'admin-status--active' : 'admin-status--inactive'
                      }`}>
                        {admin.is_active ? 'Активний' : 'Неактивний'}
                      </span>
                    </td>
                    <td className="admin-table__cell">
                      {formatDate(admin.last_login_at)}
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
                          className="admin-btn admin-btn--small admin-btn--warning"
                          title="Редагувати"
                        >
                          <PencilIcon className="w-4 h-4" />
                        </button>
                        <button 
                          className={`admin-btn admin-btn--small ${
                            admin.is_active ? 'admin-btn--warning' : 'admin-btn--success'
                          }`}
                          title={admin.is_active ? 'Деактивувати' : 'Активувати'}
                          onClick={() => handleToggleAdmin(admin.id, admin.is_active)}
                        >
                          {admin.is_active ? '⏸️' : '▶️'}
                        </button>
                        <button 
                          className="admin-btn admin-btn--small admin-btn--danger"
                          title="Видалити"
                          onClick={() => handleDeleteAdmin(admin.id, admin.username)}
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
                {searchTerm ? 'Адміністраторів за запитом не знайдено' : 'Адміністратори відсутні'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Create Admin Modal */}
      {showCreateModal && (
        <div className="admin-modal">
          <div className="admin-modal__content">
            <div className="admin-modal__header">
              <h3 className="admin-modal__title">Додати адміністратора</h3>
              <button 
                className="admin-modal__close"
                onClick={() => setShowCreateModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="admin-modal__body">
              <div className="admin-form">
                <div className="admin-form__row">
                  <div className="admin-form__group">
                    <label className="admin-form__label admin-form__label--required">
                      Ім'я
                    </label>
                    <input
                      type="text"
                      value={newAdminData.first_name}
                      onChange={(e) => setNewAdminData({...newAdminData, first_name: e.target.value})}
                      placeholder="Введіть ім'я"
                      className="admin-form__input"
                    />
                  </div>
                  <div className="admin-form__group">
                    <label className="admin-form__label">
                      Прізвище
                    </label>
                    <input
                      type="text"
                      value={newAdminData.last_name}
                      onChange={(e) => setNewAdminData({...newAdminData, last_name: e.target.value})}
                      placeholder="Введіть прізвище"
                      className="admin-form__input"
                    />
                  </div>
                </div>

                <div className="admin-form__group">
                  <label className="admin-form__label admin-form__label--required">
                    Username
                  </label>
                  <input
                    type="text"
                    value={newAdminData.username}
                    onChange={(e) => setNewAdminData({...newAdminData, username: e.target.value})}
                    placeholder="Введіть username"
                    className="admin-form__input"
                  />
                  <div className="admin-form__help">
                    Username повинен бути унікальним
                  </div>
                </div>

                <div className="admin-form__group">
                  <label className="admin-form__label admin-form__label--required">
                    Email
                  </label>
                  <input
                    type="email"
                    value={newAdminData.email}
                    onChange={(e) => setNewAdminData({...newAdminData, email: e.target.value})}
                    placeholder="Введіть email"
                    className="admin-form__input"
                  />
                </div>

                <div className="admin-form__group">
                  <label className="admin-form__label admin-form__label--required">
                    Пароль
                  </label>
                  <input
                    type="password"
                    value={newAdminData.password}
                    onChange={(e) => setNewAdminData({...newAdminData, password: e.target.value})}
                    placeholder="Введіть пароль"
                    className="admin-form__input"
                  />
                </div>

                <div className="admin-form__group">
                  <label className="admin-form__label">Права доступу</label>
                  <div className="admin-form__checkboxes">
                    <label className="admin-checkbox">
                      <input
                        type="checkbox"
                        checked={newAdminData.can_manage_users}
                        onChange={(e) => setNewAdminData({...newAdminData, can_manage_users: e.target.checked})}
                      />
                      <span className="admin-checkbox__label">Управління користувачами</span>
                    </label>
                    <label className="admin-checkbox">
                      <input
                        type="checkbox"
                        checked={newAdminData.can_manage_payments}
                        onChange={(e) => setNewAdminData({...newAdminData, can_manage_payments: e.target.checked})}
                      />
                      <span className="admin-checkbox__label">Управління платежами</span>
                    </label>
                    <label className="admin-checkbox">
                      <input
                        type="checkbox"
                        checked={newAdminData.can_manage_settings}
                        onChange={(e) => setNewAdminData({...newAdminData, can_manage_settings: e.target.checked})}
                      />
                      <span className="admin-checkbox__label">Управління налаштуваннями</span>
                    </label>
                    <label className="admin-checkbox">
                      <input
                        type="checkbox"
                        checked={newAdminData.can_manage_admins}
                        onChange={(e) => setNewAdminData({...newAdminData, can_manage_admins: e.target.checked})}
                      />
                      <span className="admin-checkbox__label">Управління адмінами</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
            <div className="admin-modal__footer">
              <button 
                className="admin-btn admin-btn--secondary"
                onClick={() => setShowCreateModal(false)}
              >
                Скасувати
              </button>
              <button 
                className="admin-btn admin-btn--primary"
                onClick={handleCreateAdmin}
              >
                Створити
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}