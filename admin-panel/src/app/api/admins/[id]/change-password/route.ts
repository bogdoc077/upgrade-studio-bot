import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const resolvedParams = context.params instanceof Promise ? await context.params : context.params;
    const adminId = parseInt(resolvedParams.id);
    const body = await request.json();
    
    if (isNaN(adminId)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid admin ID'
      }, { status: 400 });
    }

    if (!body.new_password || body.new_password.length < 6) {
      return NextResponse.json({
        success: false,
        error: 'Password must be at least 6 characters'
      }, { status: 400 });
    }

    // Get token from cookies
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const token = authHeader?.replace('Bearer ', '') || cookieToken;

    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Authorization required'
      }, { status: 401 });
    }

    // Call FastAPI endpoint
    const apiResponse = await fetch(`${API_BASE_URL}/api/admins/${adminId}/change-password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        new_password: body.new_password
      }),
    });

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      return NextResponse.json({
        success: false,
        error: errorData.detail || 'Failed to change password'
      }, { status: apiResponse.status });
    }

    const data = await apiResponse.json();

    return NextResponse.json({
      success: true,
      message: 'Password changed successfully'
    });

  } catch (error) {
    console.error('Change password error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}
