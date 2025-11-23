import { NextResponse, NextRequest } from 'next/server';
import { apiClient } from '@/utils/api-client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const resolvedParams = context.params instanceof Promise ? await context.params : context.params;
    const adminId = parseInt(resolvedParams.id);
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const token = authHeader?.replace('Bearer ', '') || cookieToken || '';
    const body = await request.json();
    
    if (isNaN(adminId)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid admin ID'
      }, { status: 400 });
    }

    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Authorization token required'
      }, { status: 401 });
    }

    // Прямий запит до FastAPI з токеном
    const apiResponse = await fetch(`${API_BASE_URL}/api/admins/${adminId}`, {
      method: 'PUT',
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
      message: 'Admin updated successfully',
      data: data
    });

  } catch (error) {
    console.error('Update admin error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const resolvedParams = context.params instanceof Promise ? await context.params : context.params;
    const adminId = parseInt(resolvedParams.id);
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const token = authHeader?.replace('Bearer ', '') || cookieToken || '';
    
    if (isNaN(adminId)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid admin ID'
      }, { status: 400 });
    }

    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Authorization token required'
      }, { status: 401 });
    }

    // Прямий запит до FastAPI з токеном
    const apiResponse = await fetch(`${API_BASE_URL}/api/admins/${adminId}`, {
      method: 'DELETE',
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
      message: 'Admin deleted successfully',
      data: data
    });

  } catch (error) {
    console.error('Delete admin error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}