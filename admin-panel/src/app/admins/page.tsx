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
  ClockIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import ViewModal from '@/components/ViewModal';
import DeleteConfirmModal from '@/components/DeleteConfirmModal';
import AdminEditModal from '@/components/AdminEditModal';

interface Admin {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name?: string;
  is_active: boolean;
  is_superadmin: boolean;
  created_at: string;
  last_login_at?: string;
}

export default function AdminsPage() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // View and Delete modal states
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedAdmin, setSelectedAdmin] = useState<Admin | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [newAdminData, setNewAdminData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: ''
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
          password: ''
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
    try {
      setIsDeleting(true);
      const response = await fetch(`/api/admins/${adminId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        setShowDeleteModal(false);
        setSelectedAdmin(null);
        await fetchAdmins(); // Refresh the list
      } else {
        throw new Error('Помилка видалення адміністратора');
      }
    } catch (err) {
      console.error('Error deleting admin:', err);
      alert('Помилка видалення адміністратора');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleViewAdmin = (admin: Admin) => {
    setSelectedAdmin(admin);
    setShowViewModal(true);
  };

  const handleDeleteClick = (admin: Admin) => {
    setSelectedAdmin(admin);
    setShowDeleteModal(true);
  };

  const handleEditAdmin = (admin: Admin) => {
    setSelectedAdmin(admin);
    setShowEditModal(true);
  };

  const handleSaveAdmin = async (adminId: number, data: Partial<Admin>) => {
    try {
      const response = await fetch(`/api/admins/${adminId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        await fetchAdmins(); // Refresh the list
      } else {
        throw new Error('Помилка оновлення адміністратора');
      }
    } catch (err) {
      console.error('Error updating admin:', err);
      alert('Помилка оновлення адміністратора');
      throw err;
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
        <div className="admin-loading">
          <div className="admin-loading__spinner"></div>
          <p className="admin-loading__text">Завантаження адміністраторів...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="admin-alert admin-alert--danger" style={{marginBottom: 'var(--spacing-base)'}}>
          {error}
        </div>
        <button 
          onClick={fetchAdmins}
          className="admin-btn admin-btn--primary"
        >
          Спробувати знову
        </button>
      </div>
    );
  }

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header admin-page__header--with-actions">
        <div className="admin-page__title-section">
          <h1 className="admin-page__title">Адміністратори</h1>
          <p className="admin-page__subtitle">
            Управління адміністраторами системи та їх правами доступу
          </p>
        </div>
        <div className="flex gap-4 items-center">
          <div className="admin-search">
            <input
              type="text"
              placeholder="Пошук адміністраторів..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="admin-search__input"
            />
          </div>
          <button 
            className="admin-btn admin-btn--primary"
            onClick={() => setShowCreateModal(true)}
          >
            <PlusIcon className="w-4 h-4" />
            Додати адміністратора
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="admin-stats">
        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Всього адмінів</span>
            <UserGroupIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{totalAdmins}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Активні</span>
            <ShieldCheckIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{activeAdmins}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Неактивні</span>
            <ClockIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{inactiveAdmins}</div>
          </div>
        </div>
      </div>

      {/* Admins Table */}
      <div className="admin-table-container">
        <div className="admin-card__header">
          <h3 className="admin-card__title">Список адміністраторів</h3>
          <p className="admin-card__subtitle">
            Знайдено: {filteredAdmins.length} з {totalAdmins} адміністраторів
          </p>
        </div>
        {filteredAdmins.length > 0 ? (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead className="admin-table__header">
                <tr>
                  <th className="admin-table__header-cell">ID</th>
                  <th className="admin-table__header-cell">Ім'я</th>
                  <th className="admin-table__header-cell">Username</th>
                  <th className="admin-table__header-cell">Email</th>
                  <th className="admin-table__header-cell">Статус</th>
                  <th className="admin-table__header-cell">Останній вхід</th>
                  <th className="admin-table__header-cell admin-table__header-cell--actions">Дії</th>
                </tr>
              </thead>
              <tbody className="admin-table__body">
                {filteredAdmins.map((admin) => (
                  <tr key={admin.id} className="admin-table__row">
                    <td className="admin-table__cell admin-table__cell--bold">{admin.id}</td>
                    <td className="admin-table__cell">
                      {admin.first_name} {admin.last_name || ''}
                    </td>
                    <td className="admin-table__cell font-medium">{admin.username}</td>
                    <td className="admin-table__cell">{admin.email}</td>
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
                    <td className="admin-table__cell admin-table__cell--actions">
                      <div className="flex items-center justify-center gap-2">
                        <button 
                          className="admin-btn admin-btn--sm admin-btn--secondary"
                          title="Переглянути"
                          onClick={() => handleViewAdmin(admin)}
                        >
                        <EyeIcon className="w-4 h-4" />
                      </button>
                      <button 
                        className="admin-btn admin-btn--sm admin-btn--secondary"
                        title="Редагувати"
                        onClick={() => handleEditAdmin(admin)}
                      >
                        <PencilIcon className="w-4 h-4" />
                      </button>
                      <button 
                        className="admin-btn admin-btn--sm admin-btn--danger"
                        title="Видалити"
                        onClick={() => handleDeleteClick(admin)}
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
        ) : (
          <div className="admin-table__empty">
            <UserGroupIcon className="admin-table__empty-icon" />
            <p className="admin-table__empty-text">
              {searchTerm ? 'Адміністраторів за запитом не знайдено' : 'Адміністратори відсутні'}
            </p>
          </div>
        )}
      </div>

      {/* Create Admin Modal */}
      {showCreateModal && (
        <div className="admin-modal" onClick={() => setShowCreateModal(false)}>
          <div className="admin-modal__backdrop" />
          <div className="admin-modal__content admin-modal__content--lg" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal__header">
              <h2 className="admin-modal__title">Додати адміністратора</h2>
              <button 
                className="admin-modal__close"
                onClick={() => setShowCreateModal(false)}
                type="button"
                title="Закрити"
              >
                <XMarkIcon />
              </button>
            </div>
            <form onSubmit={handleCreateAdmin}>
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
                </div>
              </div>
            </form>
            <div className="admin-modal__actions">
              <button 
                className="admin-btn admin-btn--secondary"
                onClick={() => setShowCreateModal(false)}
                type="button"
              >
                Скасувати
              </button>
              <button 
                className="admin-btn admin-btn--primary"
                onClick={handleCreateAdmin}
                type="button"
              >
                Створити
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {selectedAdmin && (
        <ViewModal
          isOpen={showViewModal}
          onClose={() => {
            setShowViewModal(false);
            setSelectedAdmin(null);
          }}
          title="Деталі адміністратора"
          fields={[
            { label: 'ID', value: selectedAdmin.id },
            { label: 'Username', value: selectedAdmin.username },
            { label: 'Email', value: selectedAdmin.email },
            { label: "Ім'я", value: `${selectedAdmin.first_name} ${selectedAdmin.last_name || ''}`.trim() },
            { label: 'Статус', value: selectedAdmin.is_active ? 'Активний' : 'Неактивний', type: 'status' },
            { label: 'Суперадмін', value: selectedAdmin.is_superadmin, type: 'boolean' },
            { label: 'Дата створення', value: selectedAdmin.created_at, type: 'date' },
            { label: 'Останній вхід', value: selectedAdmin.last_login_at, type: 'date' },
          ]}
        />
      )}

      {/* Edit Modal */}
      <AdminEditModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedAdmin(null);
        }}
        admin={selectedAdmin}
        onSave={handleSaveAdmin}
      />

      {/* Delete Confirmation Modal */}
      {selectedAdmin && (
        <DeleteConfirmModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setSelectedAdmin(null);
          }}
          onConfirm={() => handleDeleteAdmin(selectedAdmin.id, selectedAdmin.username)}
          title="Видалити адміністратора?"
          message="Ця дія незворотна. Адміністратор втратить доступ до панелі."
          itemName={`${selectedAdmin.username} (${selectedAdmin.email})`}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
}