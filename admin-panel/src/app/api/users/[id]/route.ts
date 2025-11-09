import { NextResponse, NextRequest } from 'next/server';
import { apiClient } from '@/utils/api-client';

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

    const response = await apiClient.deleteUser(userId);
    
    if (!response.success) {
      return NextResponse.json({
        success: false,
        error: response.error || 'Failed to delete user'
      }, { status: 500 });
    }

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

    // Оновлення підписки
    if (body.action && ['activate', 'deactivate', 'extend'].includes(body.action)) {
      const response = await apiClient.updateUserSubscription(userId, body.action);
      
      if (!response.success) {
        return NextResponse.json({
          success: false,
          error: response.error || 'Failed to update subscription'
        }, { status: 500 });
      }

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