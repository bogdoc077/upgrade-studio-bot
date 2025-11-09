import { NextResponse, NextRequest } from 'next/server';
import { apiClient } from '@/utils/api-client';

export async function GET(request: NextRequest) {
  try {
    // Отримання токена з cookies або заголовків
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const token = authHeader?.replace('Bearer ', '') || cookieToken || '';

    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Authorization token required'
      }, { status: 401 });
    }

    // Прямий запит до FastAPI з токеном
    const apiResponse = await fetch('http://localhost:8000/api/admins', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      return NextResponse.json({
        success: false,
        error: errorData.detail || `FastAPI error: ${apiResponse.status}`
      }, { status: apiResponse.status });
    }

    const data = await apiResponse.json();
    
    return NextResponse.json({
      success: true,
      data: data.admins || []
    });

  } catch (error) {
    console.error('Admins API error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch admins',
      data: []
    }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const token = authHeader?.replace('Bearer ', '') || cookieToken || '';
    const body = await request.json();

    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Authorization token required'
      }, { status: 401 });
    }

    // Прямий запит до FastAPI з токеном
    const apiResponse = await fetch('http://localhost:8000/api/admins', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      return NextResponse.json({
        success: false,
        error: errorData.detail || `FastAPI error: ${apiResponse.status}`
      }, { status: apiResponse.status });
    }

    const data = await apiResponse.json();
    
    return NextResponse.json({
      success: true,
      message: 'Admin created successfully',
      data: data
    });

  } catch (error) {
    console.error('Create admin error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}