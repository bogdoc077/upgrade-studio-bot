import { NextResponse, NextRequest } from 'next/server';
import { apiClient } from '@/utils/api-client';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');

    const response = await apiClient.getPayments({ page, limit });
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to fetch payments');
    }

    return NextResponse.json({
      success: true,
      data: response.data.payments || [],
      pagination: response.data.pagination || {}
    });

  } catch (error) {
    console.error('Payments API error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch payments',
      data: [],
      pagination: {
        current_page: 1,
        total_pages: 0,
        total_payments: 0,
        per_page: 50
      }
    }, { status: 500 });
  }
}