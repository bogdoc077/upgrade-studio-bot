'use client'

import { useState, useEffect } from 'react'
import { DetailedSetting, apiClient, handleApiError } from '@/utils/api'
import {
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  EyeIcon,
  EyeSlashIcon,
  KeyIcon,
  GlobeAltIcon,
  CurrencyEuroIcon,
  CogIcon,
} from '@heroicons/react/24/outline'

interface SettingEditModalProps {
  isOpen: boolean
  onClose: () => void
  setting: DetailedSetting | null
  onSuccess: () => void
}

const getCategoryIcon = (category: string) => {
  switch (category.toLowerCase()) {
    case 'bot':
      return KeyIcon
    case 'payment':
    case 'stripe':
      return CurrencyEuroIcon
    case 'webhook':
      return GlobeAltIcon
    default:
      return CogIcon
  }
}

export default function SettingEditModal({ isOpen, onClose, setting, onSuccess }: SettingEditModalProps) {
  const [loading, setLoading] = useState(false)
  const [showValue, setShowValue] = useState(false)
  const [formData, setFormData] = useState({
    value: '',
    description: ''
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Ініціалізуємо форму коли відкривається модал
  useEffect(() => {
    if (isOpen && setting) {
      setFormData({
        value: setting.is_sensitive ? '' : setting.decrypted_value,
        description: setting.description || ''
      })
      setErrors({})
      setShowValue(false)
    }
  }, [isOpen, setting])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Очищуємо помилку для цього поля
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.value.trim()) {
      newErrors.value = "Значення є обов'язковим"
    }

    // Спеціальні валідації для певних типів
    if (setting?.key.includes('email')) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(formData.value)) {
        newErrors.value = "Невірний формат email"
      }
    }

    if (setting?.key.includes('price')) {
      const price = parseInt(formData.value)
      if (isNaN(price) || price < 0) {
        newErrors.value = "Ціна повинна бути числом більше 0"
      }
    }

    if (setting?.key.includes('url')) {
      try {
        new URL(formData.value)
      } catch {
        newErrors.value = "Невірний формат URL"
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!setting || !validateForm()) return
    
    setLoading(true)
    
    try {
      await apiClient.updateSetting(setting.key, {
        value: formData.value,
        value_type: setting.value_type,
        category: setting.category,
        is_sensitive: setting.is_sensitive,
        description: formData.description
      })
      
      onSuccess()
      onClose()
    } catch (err) {
      const errorMessage = handleApiError(err)
      setErrors({ general: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !setting) return null

  const CategoryIcon = getCategoryIcon(setting.category)

  return (
    <div className="modal">
      <div className="modal__backdrop" onClick={onClose}></div>
      <div className="modal__container">
        <div className="modal__content-wrapper">
          <form onSubmit={handleSubmit} className="modal__panel">
            <div className="modal__header">
              <h3 className="modal__title">
                <CategoryIcon className="modal__title-icon" />
                Редагувати налаштування
              </h3>
              <p className="modal__subtitle">
                {setting.key.replace(/_/g, ' ').toUpperCase()}
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
                <div className="form-section">
                  <h4 className="form-section__title">
                    <CogIcon className="form-section__icon" />
                    Інформація про налаштування
                  </h4>
                  
                  <div className="user-edit__info-grid">
                    <div className="user-edit__info-item">
                      <span className="user-edit__info-label">Ключ:</span>
                      <span className="user-edit__info-value">{setting.key}</span>
                    </div>
                    <div className="user-edit__info-item">
                      <span className="user-edit__info-label">Категорія:</span>
                      <span className="user-edit__info-value">{setting.category}</span>
                    </div>
                    <div className="user-edit__info-item">
                      <span className="user-edit__info-label">Тип:</span>
                      <span className="user-edit__info-value">{setting.value_type}</span>
                    </div>
                    <div className="user-edit__info-item">
                      <span className="user-edit__info-label">Конфіденційне:</span>
                      <span className="user-edit__info-value">
                        {setting.is_sensitive ? 'Так' : 'Ні'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="form-section">
                  <h4 className="form-section__title">
                    <PencilIcon className="form-section__icon" />
                    Редагування значення
                  </h4>

                  <div className="form-group">
                    <label className="form-label" htmlFor="value">
                      Значення *
                    </label>
                    {setting.is_sensitive ? (
                      <div className="form-input-group">
                        <input
                          type={showValue ? 'text' : 'password'}
                          id="value"
                          className={`form-input ${errors.value ? 'form-input--error' : ''}`}
                          value={formData.value}
                          onChange={(e) => handleInputChange('value', e.target.value)}
                          placeholder={setting.is_sensitive ? 'Введіть нове значення' : ''}
                          disabled={loading}
                        />
                        <button
                          type="button"
                          className="form-input-addon"
                          onClick={() => setShowValue(!showValue)}
                        >
                          {showValue ? <EyeSlashIcon /> : <EyeIcon />}
                        </button>
                      </div>
                    ) : (
                      <input
                        type="text"
                        id="value"
                        className={`form-input ${errors.value ? 'form-input--error' : ''}`}
                        value={formData.value}
                        onChange={(e) => handleInputChange('value', e.target.value)}
                        disabled={loading}
                      />
                    )}
                    {errors.value && (
                      <div className="form-error">{errors.value}</div>
                    )}
                    {setting.is_sensitive && (
                      <p className="form-helper">
                        Залиште порожнім, якщо не хочете змінювати поточне значення
                      </p>
                    )}
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="description">
                      Опис
                    </label>
                    <textarea
                      id="description"
                      className="form-input"
                      rows={3}
                      value={formData.description}
                      onChange={(e) => handleInputChange('description', e.target.value)}
                      placeholder="Опис налаштування..."
                      disabled={loading}
                    />
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
                    Збереження...
                  </>
                ) : (
                  <>
                    <CheckIcon className="btn__icon" />
                    Зберегти
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

// Додаємо helper стилі
const styles = `
.form-helper {
  font-size: 0.75rem;
  color: var(--color-gray-500);
  margin-top: 0.25rem;
  font-style: italic;
}

.form-input[type="textarea"] {
  resize: vertical;
  min-height: 80px;
}
`

// Додаємо стилі до документа
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style')
  styleElement.textContent = styles
  document.head.appendChild(styleElement)
}