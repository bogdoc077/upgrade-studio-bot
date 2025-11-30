import { NextResponse, NextRequest } from 'next/server';

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');
    const search = searchParams.get('search') || '';
    const status = searchParams.get('status') || '';
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
    if (status) queryParams.append('status', status);
    if (dateFrom) queryParams.append('date_from', dateFrom);
    if (dateTo) queryParams.append('date_to', dateTo);
    
    const query = queryParams.toString();
    const url = `${API_BASE_URL}/api/payments${query ? `?${query}` : ''}`;
    
    console.log('Making request to FastAPI payments:', url);
    
    const apiResponse = await fetch(url, {
      headers: {
        'Authorization': authHeader,
      },
    });

    console.log('FastAPI payments response status:', apiResponse.status);

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      console.log('FastAPI payments error:', errorData);
      throw new Error(errorData.detail || `HTTP ${apiResponse.status}`);
    }

    const response = await apiResponse.json();
    console.log('FastAPI payments response data:', response);

    return NextResponse.json({
      success: true,
      data: response.data || [],
      total: response.total || 0,
      pagination: response.pagination || {}
    });

  } catch (error) {
    console.error('Payments API error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch payments',
      data: [],
      total: 0,
      pagination: {
        current_page: 1,
        total_pages: 0,
        total_payments: 0,
        per_page: 50
      }
    }, { status: 500 });
  }
}
