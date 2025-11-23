'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface Admin {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name?: string;
  is_active: boolean;
}

interface AdminEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  admin: Admin | null;
  onSave: (adminId: number, data: Partial<Admin>) => Promise<void>;
}

export default function AdminEditModal({ isOpen, onClose, admin, onSave }: AdminEditModalProps) {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    is_active: true,
  });
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen && admin) {
      setFormData({
        email: admin.email,
        first_name: admin.first_name,
        last_name: admin.last_name || '',
        is_active: admin.is_active,
      });
    }
  }, [isOpen, admin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!admin) return;
    
    setIsSaving(true);
    try {
      await onSave(admin.id, formData);
      onClose();
    } catch (error) {
      console.error('Error saving admin:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen || !admin) return null;

  return (
    <div className="admin-modal" onClick={onClose}>
      <div className="admin-modal__backdrop" />
      <div className="admin-modal__content admin-modal__content--lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal__header">
          <h2 className="admin-modal__title">Редагувати адміністратора</h2>
          <button
            onClick={onClose}
            className="admin-modal__close"
            type="button"
            title="Закрити"
          >
            <XMarkIcon />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="admin-modal__body">
            <div className="admin-form">
              <div className="admin-form__row">
                <div className="admin-form__group">
                  <label className="admin-form__label">
                    Ім'я *
                  </label>
                  <input
                    type="text"
                    className="admin-form__input"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    required
                  />
                </div>

                <div className="admin-form__group">
                  <label className="admin-form__label">
                    Прізвище
                  </label>
                  <input
                    type="text"
                    className="admin-form__input"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  />
                </div>
              </div>

              <div className="admin-form__group">
                <label className="admin-form__label">
                  Email *
                </label>
                <input
                  type="email"
                  className="admin-form__input"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>

              <div className="admin-form__group">
                <label className="admin-form__label" style={{ display: 'flex', alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    style={{ marginRight: '8px' }}
                  />
                  Активний
                </label>
              </div>

              <div className="admin-alert admin-alert--info" style={{ marginTop: 'var(--spacing-base)' }}>
                <strong>Інформація:</strong> Username адміністратора не можна редагувати
              </div>
            </div>
          </div>

          <div className="admin-modal__actions">
            <button
              type="button"
              onClick={onClose}
              className="admin-btn admin-btn--secondary"
              disabled={isSaving}
            >
              Скасувати
            </button>
            <button
              type="submit"
              className="admin-btn admin-btn--primary"
              disabled={isSaving}
            >
              {isSaving ? 'Збереження...' : 'Зберегти'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
