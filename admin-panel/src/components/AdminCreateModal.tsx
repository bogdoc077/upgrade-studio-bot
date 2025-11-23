'use client'

import { useState } from 'react'
import { apiClient, handleApiError } from '@/utils/api'
import {
  UserIcon,
  ShieldCheckIcon,
  KeyIcon,
  XMarkIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline'

interface AdminCreateModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

interface CreateAdminForm {
  username: string
  email: string
  first_name: string
  last_name: string
  password: string
  confirm_password: string
  is_active: boolean
}

export default function AdminCreateModal({ isOpen, onClose, onSuccess }: AdminCreateModalProps) {
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  
  const [form, setForm] = useState<CreateAdminForm>({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    confirm_password: '',
    is_active: true,
  })

  const handleInputChange = (field: keyof CreateAdminForm, value: string | boolean) => {
    setForm(prev => ({ ...prev, [field]: value }))
    // Очищуємо помилку для цього поля
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!form.username.trim()) {
      newErrors.username = "Username є обов'язковим"
    } else if (form.username.length < 3) {
      newErrors.username = "Username повинен бути мінімум 3 символи"
    }

    if (!form.email.trim()) {
      newErrors.email = "Email є обов'язковим"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      newErrors.email = "Невірний формат email"
    }

    if (!form.first_name.trim()) {
      newErrors.first_name = "Ім'я є обов'язковим"
    }

    if (!form.password) {
      newErrors.password = "Пароль є обов'язковим"
    } else if (form.password.length < 6) {
      newErrors.password = "Пароль повинен бути мінімум 6 символів"
    }

    if (form.password !== form.confirm_password) {
      newErrors.confirm_password = "Паролі не збігаються"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return
    
    setLoading(true)
    
    try {
      const { confirm_password, ...adminData } = form
      await apiClient.createAdmin(adminData)
      
      onSuccess()
      onClose()
      
      // Скидаємо форму
      setForm({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        password: '',
        confirm_password: '',
        is_active: true,
      })
    } catch (err) {
      const errorMessage = handleApiError(err)
      setErrors({ general: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal">
      <div className="modal__backdrop" onClick={onClose}></div>
      <div className="modal__container">
        <div className="modal__content-wrapper modal__content-wrapper--large">
          <form onSubmit={handleSubmit} className="modal__panel">
            <div className="modal__header">
              <h3 className="modal__title">
                <ShieldCheckIcon className="modal__title-icon" />
                Додати нового адміністратора
              </h3>
              <p className="modal__subtitle">
                Створіть новий обліковий запис для адміністратора системи
              </p>
              <button
                type="button"
                onClick={onClose}
                className="modal__close-btn"
                disabled={loading}
              >
                <XMarkIcon />
              </button>
            </div>

            <div className="modal__body">
              {errors.general && (
                <div className="alert alert--error">
                  <div className="alert__content">{errors.general}</div>
                </div>
              )}

              <div className="form-grid">
                {/* Особисті дані */}
                <div className="form-section">
                  <h4 className="form-section__title">
                    <UserIcon className="form-section__icon" />
                    Особисті дані
                  </h4>
                  
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label" htmlFor="first_name">
                        Ім'я *
                      </label>
                      <input
                        type="text"
                        id="first_name"
                        className={`form-input ${errors.first_name ? 'form-input--error' : ''}`}
                        value={form.first_name}
                        onChange={(e) => handleInputChange('first_name', e.target.value)}
                        placeholder="Введіть ім'я"
                        disabled={loading}
                      />
                      {errors.first_name && (
                        <div className="form-error">{errors.first_name}</div>
                      )}
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="last_name">
                        Прізвище
                      </label>
                      <input
                        type="text"
                        id="last_name"
                        className="form-input"
                        value={form.last_name}
                        onChange={(e) => handleInputChange('last_name', e.target.value)}
                        placeholder="Введіть прізвище"
                        disabled={loading}
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label" htmlFor="username">
                        Username *
                      </label>
                      <input
                        type="text"
                        id="username"
                        className={`form-input ${errors.username ? 'form-input--error' : ''}`}
                        value={form.username}
                        onChange={(e) => handleInputChange('username', e.target.value)}
                        placeholder="Введіть username"
                        disabled={loading}
                      />
                      {errors.username && (
                        <div className="form-error">{errors.username}</div>
                      )}
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="email">
                        Email *
                      </label>
                      <input
                        type="email"
                        id="email"
                        className={`form-input ${errors.email ? 'form-input--error' : ''}`}
                        value={form.email}
                        onChange={(e) => handleInputChange('email', e.target.value)}
                        placeholder="Введіть email"
                        disabled={loading}
                      />
                      {errors.email && (
                        <div className="form-error">{errors.email}</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Безпека */}
                <div className="form-section">
                  <h4 className="form-section__title">
                    <KeyIcon className="form-section__icon" />
                    Безпека
                  </h4>
                  
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label" htmlFor="password">
                        Пароль *
                      </label>
                      <div className="form-input-group">
                        <input
                          type={showPassword ? 'text' : 'password'}
                          id="password"
                          className={`form-input ${errors.password ? 'form-input--error' : ''}`}
                          value={form.password}
                          onChange={(e) => handleInputChange('password', e.target.value)}
                          placeholder="Введіть пароль"
                          disabled={loading}
                        />
                        <button
                          type="button"
                          className="form-input-addon"
                          onClick={() => setShowPassword(!showPassword)}
                        >
                          {showPassword ? <EyeSlashIcon /> : <EyeIcon />}
                        </button>
                      </div>
                      {errors.password && (
                        <div className="form-error">{errors.password}</div>
                      )}
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="confirm_password">
                        Підтвердити пароль *
                      </label>
                      <div className="form-input-group">
                        <input
                          type={showConfirmPassword ? 'text' : 'password'}
                          id="confirm_password"
                          className={`form-input ${errors.confirm_password ? 'form-input--error' : ''}`}
                          value={form.confirm_password}
                          onChange={(e) => handleInputChange('confirm_password', e.target.value)}
                          placeholder="Підтвердіть пароль"
                          disabled={loading}
                        />
                        <button
                          type="button"
                          className="form-input-addon"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        >
                          {showConfirmPassword ? <EyeSlashIcon /> : <EyeIcon />}
                        </button>
                      </div>
                      {errors.confirm_password && (
                        <div className="form-error">{errors.confirm_password}</div>
                      )}
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-checkbox">
                      <input
                        type="checkbox"
                        checked={form.is_active}
                        onChange={(e) => handleInputChange('is_active', e.target.checked)}
                        disabled={loading}
                      />
                      <span className="form-checkbox__checkmark"></span>
                      <span className="form-checkbox__label">Активний аккаунт</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal__footer">
              <button
                type="button"
                onClick={onClose}
                className="btn btn--secondary"
                disabled={loading}
              >
                Скасувати
              </button>
              <button
                type="submit"
                className="btn btn--primary"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <div className="btn__loader"></div>
                    Створення...
                  </>
                ) : (
                  <>
                    <ShieldCheckIcon className="btn__icon" />
                    Створити адміна
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}