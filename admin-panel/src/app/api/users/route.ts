import { NextResponse, NextRequest } from 'next/server';

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');
    const search = searchParams.get('search') || '';
    const subscriptionStatus = searchParams.get('subscription_status') || '';
    const dateFrom = searchParams.get('date_from') || '';
    const dateTo = searchParams.get('date_to') || '';

    // Отримуємо токен авторизації з заголовків
    const authHeader = request.headers.get('authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { success: false, error: 'Authorization required' },
        { status: 401 }
      );
    }

    // Робимо прямий запит до FastAPI з токеном
    const queryParams = new URLSearchParams();
    if (page) queryParams.append('page', page.toString());
    if (limit) queryParams.append('limit', limit.toString());
    if (search) queryParams.append('search', search);
    if (subscriptionStatus) queryParams.append('subscription_status', subscriptionStatus);
    if (dateFrom) queryParams.append('date_from', dateFrom);
    if (dateTo) queryParams.append('date_to', dateTo);
    
    const query = queryParams.toString();
    const url = `${API_BASE_URL}/api/users${query ? `?${query}` : ''}`;
    
    console.log('Making request to FastAPI:', url);
    
    const apiResponse = await fetch(url, {
      headers: {
        'Authorization': authHeader,
      },
    });

    console.log('FastAPI response status:', apiResponse.status);

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      console.log('FastAPI error:', errorData);
      throw new Error(errorData.detail || `HTTP ${apiResponse.status}`);
    }

    const response = await apiResponse.json();
    console.log('FastAPI response data:', response);

    return NextResponse.json({
      success: true,
      data: response.data || [],
      total: response.total || 0,
      stats: response.stats || {
        total: 0,
        active: 0,
        paused: 0,
        cancelled: 0,
        inactive: 0
      },
      pagination: response.pagination || {}
    });

  } catch (error) {
    console.error('Users API error:', error);
    
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch users',
      data: [],
      pagination: {
        current_page: 1,
        total_pages: 0,
        total_users: 0,
        per_page: 50
      }
    }, { status: 500 });
  }
}
