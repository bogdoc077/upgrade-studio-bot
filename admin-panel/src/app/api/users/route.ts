import { NextResponse, NextRequest } from 'next/server';
import { apiClient } from '@/utils/api-client';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');
    const search = searchParams.get('search') || '';

    const response = await apiClient.getUsers({ page, limit, search });
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to fetch users');
    }

    return NextResponse.json({
      success: true,
      data: response.data.users || [],
      pagination: response.data.pagination || {}
    });

  } catch (error) {
    console.error('Users API error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch users',
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