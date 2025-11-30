import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('admin_token')?.value;

    if (!token) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Передаємо всі query параметри
    const searchParams = request.nextUrl.searchParams;
    const queryString = searchParams.toString();
    
    const response = await fetch(
      `${API_BASE_URL}/api/system-logs${queryString ? `?${queryString}` : ''}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error fetching system logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch system logs', details: error.message },
      { status: 500 }
    );
  }
}
