import { NextResponse, NextRequest } from 'next/server';

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const resolvedParams = context.params instanceof Promise ? await context.params : context.params;
    const userId = parseInt(resolvedParams.id);
    
    if (isNaN(userId)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid user ID'
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

    // Direct call to FastAPI
    const apiResponse = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
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
        error: errorData.detail || 'Failed to delete user'
      }, { status: apiResponse.status });
    }

    const data = await apiResponse.json();

    return NextResponse.json({
      success: true,
      message: 'User deleted successfully'
    });

  } catch (error) {
    console.error('Delete user error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ id: string }> | { id: string } }
) {
  try {
    const resolvedParams = context.params instanceof Promise ? await context.params : context.params;
    const userId = parseInt(resolvedParams.id);
    const body = await request.json();
    
    if (isNaN(userId)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid user ID'
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

    // Оновлення підписки
    if (body.action && ['activate', 'deactivate', 'extend'].includes(body.action)) {
      const apiResponse = await fetch(`${API_BASE_URL}/api/users/${userId}/subscription/${body.action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!apiResponse.ok) {
        const errorData = await apiResponse.json().catch(() => ({}));
        return NextResponse.json({
          success: false,
          error: errorData.detail || 'Failed to update subscription'
        }, { status: apiResponse.status });
      }

      const data = await apiResponse.json();

      return NextResponse.json({
        success: true,
        message: `Subscription ${body.action} successful`
      });
    }

    return NextResponse.json({
      success: false,
      error: 'Invalid action'
    }, { status: 400 });

  } catch (error) {
    console.error('Update user error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Internal server error'
    }, { status: 500 });
  }
}