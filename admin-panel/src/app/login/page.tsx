'use client'

import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  ShieldCheckIcon,
  EyeIcon,
  EyeSlashIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'

function LoginForm() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectTo = searchParams.get('redirect') || '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Помилка авторизації')
      }

      const data = await response.json()
      
      // Зберігаємо токен та дані адміна
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('admin_data', JSON.stringify(data.admin))
      
      // Встановлюємо cookie для middleware
      document.cookie = `auth_token=${data.access_token}; path=/; max-age=${24 * 60 * 60}`
      
      // Перенаправляємо
      router.push(redirectTo)
      
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  return (
    <div className="login-page">
      <div className="login__container">
        <div className="login__card">
          {/* Header */}
          <div className="login__header">
            <div className="login__logo">
              <ShieldCheckIcon className="login__logo-icon" />
              <h1 className="login__title">Upgrade Studio</h1>
            </div>
            <p className="login__subtitle">Адміністративна панель</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="login__form">
            {error && (
              <div className="alert alert--error">
                <div className="alert__content">
                  <ExclamationCircleIcon className="w-5 h-5 mr-2" />
                  {error}
                </div>
              </div>
            )}

            {/* Username */}
            <div className="login__field">
              <label htmlFor="username" className="login__label">
                Ім'я користувача
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                value={formData.username}
                onChange={handleChange}
                className="login__input"
                placeholder="Введіть ім'я користувача"
              />
            </div>

            {/* Password */}
            <div className="login__field">
              <label htmlFor="password" className="login__label">
                Пароль
              </label>
              <div className="login__password-field">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={formData.password}
                  onChange={handleChange}
                  className="login__input login__input--password"
                  placeholder="Введіть пароль"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="login__password-toggle"
                >
                  {showPassword ? (
                    <EyeSlashIcon className="w-5 h-5" />
                  ) : (
                    <EyeIcon className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn btn--primary login__submit"
            >
              {loading ? (
                <div className="flex items-center">
                  <div className="loader loader--small mr-2"></div>
                  Вхід...
                </div>
              ) : (
                'Увійти'
              )}
            </button>
          </form>

          {/* Default credentials info */}
          <div className="login__info">
            <p className="login__info-text">
              Дефолтні дані для входу:
            </p>
            <p className="login__credentials">
              <strong>Користувач:</strong> admin<br />
              <strong>Пароль:</strong> admin123
            </p>
            <p className="login__warning">
              ⚠️ Змініть пароль після першого входу!
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Login() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LoginForm />
    </Suspense>
  )
}