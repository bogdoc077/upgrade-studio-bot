import { NextResponse } from 'next/server';
import { apiClient } from '@/utils/api-client';

export async function GET() {
  try {
    // Get dashboard stats from FastAPI
    const dashboardResponse = await apiClient.getDashboard();
    
    // Get recent users and payments for activity feed
    const [usersResponse, paymentsResponse] = await Promise.all([
      apiClient.getUsers().catch(() => []),
      apiClient.getPayments().catch(() => [])
    ]);

    // Use real data from FastAPI
    const stats = dashboardResponse?.data || {
      total_users: 0,
      active_users: 0,
      inactive_users: 0,
      total_revenue: 0,
      payments_today: 0
    };

    return NextResponse.json({
      success: true,
      data: {
        stats,
        recent_activity: {
          users: Array.isArray(usersResponse) ? usersResponse.slice(0, 5) : [],
          payments: Array.isArray(paymentsResponse) ? paymentsResponse.slice(0, 5) : []
        }
      }
    });

  } catch (error) {
    console.error('Dashboard API error:', error);
    
    // Return empty data structure on error (no mock data)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch dashboard data',
      data: {
        stats: {
          total_users: 0,
          active_users: 0,
          inactive_users: 0,
          total_revenue: 0,
          payments_today: 0
        },
        recent_activity: {
          users: [],
          payments: []
        }
      }
    }, { status: 500 });
  }
}
