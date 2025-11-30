import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth_token')?.value;

    console.log('[system-logs] Token present:', !!token);

    if (!token) {
      console.log('[system-logs] No auth token found in cookies');
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Передаємо всі query параметри
    const { searchParams } = new URL(request.url);
    const page = searchParams.get('page') || '1';
    const limit = searchParams.get('limit') || '50';
    const task_type = searchParams.get('task_type');
    const status = searchParams.get('status');
    
    let queryString = `page=${page}&limit=${limit}`;
    if (task_type) queryString += `&task_type=${task_type}`;
    if (status) queryString += `&status=${status}`;
    
    const apiUrl = `${API_BASE_URL}/api/system-logs?${queryString}`;
    console.log('[system-logs] Fetching from:', apiUrl);
    
    const response = await fetch(
      apiUrl,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      }
    );

    console.log('[system-logs] API response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[system-logs] API error:', response.status, errorText);
      return NextResponse.json(
        { error: 'Failed to fetch system logs', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('[system-logs] Success, returned', data.data?.length || 0, 'logs');
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('[system-logs] Exception:', error);
    return NextResponse.json(
      { error: 'Failed to fetch system logs', details: error.message },
      { status: 500 }
    );
  }
}
