import axios, { AxiosResponse } from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Створюємо екземпляр axios з базовими налаштуваннями
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// Додаємо interceptor для автоматичного додавання токена
api.interceptors.request.use((config) => {
  // Спробуємо отримати токен з localStorage
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  
  // Fallback до Basic Auth якщо немає токена
  if (!config.headers.Authorization) {
    const username = process.env.NEXT_PUBLIC_ADMIN_USERNAME || 'admin'
    const password = process.env.NEXT_PUBLIC_ADMIN_PASSWORD || 'admin123'
    const credentials = btoa(`${username}:${password}`)
    config.headers.Authorization = `Basic ${credentials}`
  }
  
  return config
})

// Додаємо interceptor для обробки помилок авторизації
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Видаляємо токен та перенаправляємо на логін
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('admin_data')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Типи даних
export interface User {
  id: number
  telegram_id: number
  username?: string
  first_name?: string
  last_name?: string
  state: string
  role: string
  subscription_status: string
  subscription_active: boolean
  subscription_end_date?: string
  joined_channel: boolean
  joined_chat: boolean
  created_at: string
  updated_at: string
}

export interface Payment {
  id: number
  user_id: number
  stripe_payment_intent_id?: string
  amount: number
  currency: string
  status: string
  created_at: string
  updated_at?: string
  paid_at?: string
  telegram_id: number
  first_name?: string
  last_name?: string
}

export interface DashboardStats {
  total_users: number
  active_subscribers: number
  total_revenue: number
  conversion_rate: number
  recent_payments: Payment[]
}

export interface PaginatedUsers {
  users: User[]
  pagination: {
    current_page: number
    total_pages: number
    total_users: number
    per_page: number
  }
}

export interface PaginatedPayments {
  payments: Payment[]
  pagination: {
    current_page: number
    total_pages: number
    total_payments: number
    per_page: number
  }
}

export interface Settings {
  bot_token: string
  webhook_url: string
  stripe_publishable_key: string
  stripe_secret_key: string
  stripe_webhook_secret: string
  subscription_price: number
  subscription_currency: string
  database_status: string
  bot_status: string
  webhook_status: string
  app_name: string
  support_email: string
  maintenance_mode: boolean
}

export interface DetailedSetting {
  id: number
  key: string
  encrypted_value: string
  decrypted_value: string
  value_type: string
  category: string
  is_sensitive: boolean
  description?: string
  created_at: string
  updated_at?: string
  updated_by?: number
  updated_by_username?: string
}

export interface SettingsResponse {
  settings: DetailedSetting[]
}

export interface SettingUpdateData {
  value: string
  value_type?: string
  category?: string
  is_sensitive?: boolean
  description?: string
}

export interface Admin {
  id: number
  username: string
  email: string
  first_name: string
  last_name?: string
  is_active: boolean
  is_superadmin: boolean
  created_at: string
  last_login_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  admin: Admin
}

export interface PaginatedAdmins {
  admins: Admin[]
}

// API функції
export const apiClient = {
  // Dashboard
  getDashboardStats: (): Promise<AxiosResponse<DashboardStats>> =>
    api.get('/api/dashboard'),

  // Users
  getUsers: (page = 1, limit = 50, search = ''): Promise<AxiosResponse<PaginatedUsers>> =>
    api.get('/api/users', { params: { page, limit, search } }),

  updateUserSubscription: (userId: number, action: 'activate' | 'deactivate' | 'extend'): Promise<AxiosResponse<any>> =>
    api.post(`/api/users/${userId}/subscription`, { action }),

  deleteUser: (userId: number): Promise<AxiosResponse<any>> =>
    api.delete(`/api/users/${userId}`),

  // Payments
  getPayments: (page = 1, limit = 50): Promise<AxiosResponse<PaginatedPayments>> =>
    api.get('/api/payments', { params: { page, limit } }),

  // Authentication
  login: (username: string, password: string): Promise<AxiosResponse<LoginResponse>> =>
    api.post('/api/auth/login', { username, password }),

  getCurrentAdmin: (): Promise<AxiosResponse<Admin>> =>
    api.get('/api/auth/me'),

  // Admins
  getAdmins: (): Promise<AxiosResponse<PaginatedAdmins>> =>
    api.get('/api/admins'),

  createAdmin: (adminData: any): Promise<AxiosResponse<any>> =>
    api.post('/api/admins', adminData),

  updateAdmin: (adminId: number, adminData: any): Promise<AxiosResponse<any>> =>
    api.put(`/api/admins/${adminId}`, adminData),

  deleteAdmin: (adminId: number): Promise<AxiosResponse<any>> =>
    api.delete(`/api/admins/${adminId}`),

  changeAdminPassword: (adminId: number, passwordData: any): Promise<AxiosResponse<any>> =>
    api.post(`/api/admins/${adminId}/change-password`, passwordData),

  // Settings
  getSettings: (): Promise<AxiosResponse<Settings>> =>
    api.get('/api/settings'),

  getAllSettings: (): Promise<AxiosResponse<SettingsResponse>> =>
    api.get('/api/settings/all'),

  updateSetting: (key: string, data: SettingUpdateData): Promise<AxiosResponse<any>> =>
    api.put(`/api/settings/${key}`, data),
}

// Error handler
export const handleApiError = (error: any) => {
  if (error.response) {
    // Server responded with error status
    console.error('API Error:', error.response.data)
    return error.response.data.detail || 'Server error occurred'
  } else if (error.request) {
    // Request made but no response received
    console.error('Network Error:', error.request)
    return 'Network error - please check your connection'
  } else {
    // Something else happened
    console.error('Error:', error.message)
    return error.message || 'An unexpected error occurred'
  }
}