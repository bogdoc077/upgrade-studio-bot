'use client';

import { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface User {
  id: number;
  telegram_id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  goals?: string;
  injuries?: string;
  subscription_active: number;
  subscription_paused: number;
}

interface UserEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  onSave: (userId: number, data: Partial<User>) => Promise<void>;
}

export default function UserEditModal({ isOpen, onClose, user, onSave }: UserEditModalProps) {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    goals: '',
    injuries: '',
    subscription_active: 0,
    subscription_paused: 0,
  });
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen && user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        goals: user.goals || '',
        injuries: user.injuries || '',
        subscription_active: user.subscription_active,
        subscription_paused: user.subscription_paused,
      });
    }
  }, [isOpen, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    
    setIsSaving(true);
    try {
      await onSave(user.id, formData);
      onClose();
    } catch (error) {
      console.error('Error saving user:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen || !user) return null;

  return (
    <div className="admin-modal" onClick={onClose}>
      <div className="admin-modal__backdrop" />
      <div className="admin-modal__content admin-modal__content--lg" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal__header">
          <h2 className="admin-modal__title">Редагувати користувача</h2>
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
                    Ім'я
                  </label>
                  <input
                    type="text"
                    className="admin-form__input"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
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
                  Цілі
                </label>
                <textarea
                  className="admin-form__textarea"
                  value={formData.goals}
                  onChange={(e) => setFormData({ ...formData, goals: e.target.value })}
                  rows={3}
                  placeholder="Цілі тренувань користувача"
                />
              </div>

              <div className="admin-form__group">
                <label className="admin-form__label">
                  Травми / Обмеження
                </label>
                <textarea
                  className="admin-form__textarea"
                  value={formData.injuries}
                  onChange={(e) => setFormData({ ...formData, injuries: e.target.value })}
                  rows={3}
                  placeholder="Травми або обмеження користувача"
                />
              </div>

              <div className="admin-form__row">
                <div className="admin-form__group">
                  <label className="admin-form__label" style={{ display: 'flex', alignItems: 'center' }}>
                    <input
                      type="checkbox"
                      checked={formData.subscription_active === 1}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        subscription_active: e.target.checked ? 1 : 0 
                      })}
                      style={{ marginRight: '8px' }}
                    />
                    Активна підписка
                  </label>
                </div>

                <div className="admin-form__group">
                  <label className="admin-form__label" style={{ display: 'flex', alignItems: 'center' }}>
                    <input
                      type="checkbox"
                      checked={formData.subscription_paused === 1}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        subscription_paused: e.target.checked ? 1 : 0 
                      })}
                      style={{ marginRight: '8px' }}
                    />
                    Призупинена підписка
                  </label>
                </div>
              </div>

              <div className="admin-alert admin-alert--info" style={{ marginTop: 'var(--spacing-base)' }}>
                <strong>Інформація:</strong> Telegram ID та Username не можна редагувати
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