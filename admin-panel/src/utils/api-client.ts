// API client для з'єднання з FastAPI сервером
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface ApiResponse<T = any> {
  success?: boolean;
  data?: T;
  error?: string;
  message?: string;
}

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};
    
    // Спочатку пробуємо JWT токен
    if (typeof localStorage !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
        return headers;
      }
    }
    
    // Fallback до Basic Auth з дефолтними кредами
    const basicAuth = btoa('admin:admin123');
    headers['Authorization'] = `Basic ${basicAuth}`;
    
    return headers;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseURL}${endpoint}`;
      
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: errorData.detail || `HTTP ${response.status}`,
        };
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('API request failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Dashboard
  async getDashboard(): Promise<ApiResponse> {
    return this.makeRequest('/api/dashboard');
  }

  // Users
  async getUsers(params: {
    page?: number;
    limit?: number;
    search?: string;
  } = {}): Promise<ApiResponse> {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.search) queryParams.append('search', params.search);
    
    const query = queryParams.toString();
    return this.makeRequest(`/api/users${query ? `?${query}` : ''}`);
  }

  async deleteUser(userId: number): Promise<ApiResponse> {
    return this.makeRequest(`/api/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async updateUserSubscription(userId: number, action: string): Promise<ApiResponse> {
    return this.makeRequest(`/api/users/${userId}/subscription?action=${action}`, {
      method: 'POST',
    });
  }

  // Payments
  async getPayments(params: {
    page?: number;
    limit?: number;
  } = {}): Promise<ApiResponse> {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    
    const query = queryParams.toString();
    return this.makeRequest(`/api/payments${query ? `?${query}` : ''}`);
  }

  // Auth
  async login(username: string, password: string): Promise<ApiResponse> {
    return this.makeRequest('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async getCurrentUser(token: string): Promise<ApiResponse> {
    return this.makeRequest('/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  // Admins
  async getAdmins(token: string): Promise<ApiResponse> {
    return this.makeRequest('/api/admins', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async createAdmin(adminData: any, token: string): Promise<ApiResponse> {
    return this.makeRequest('/api/admins', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(adminData),
    });
  }

  async updateAdmin(adminId: number, adminData: any, token: string): Promise<ApiResponse> {
    return this.makeRequest(`/api/admins/${adminId}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(adminData),
    });
  }

  async deleteAdmin(adminId: number, token: string): Promise<ApiResponse> {
    return this.makeRequest(`/api/admins/${adminId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  // Settings
  async getSettings(): Promise<ApiResponse> {
    return this.makeRequest('/api/settings');
  }

  async getAllSettings(token: string): Promise<ApiResponse> {
    return this.makeRequest('/api/settings/all', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async updateSetting(key: string, settingData: any, token: string): Promise<ApiResponse> {
    return this.makeRequest(`/api/settings/${key}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(settingData),
    });
  }
}

export const apiClient = new ApiClient();

/**
 * Wrapper функція для прямих API викликів
 * Використовує той самий механізм авторизації що і ApiClient
 */
export async function makeApiCall(endpoint: string, options: RequestInit = {}): Promise<any> {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
  
  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {};
    
    if (typeof localStorage !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
        return headers;
      }
    }
    
    const basicAuth = btoa('admin:admin123');
    headers['Authorization'] = `Basic ${basicAuth}`;
    
    return headers;
  };
  
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}