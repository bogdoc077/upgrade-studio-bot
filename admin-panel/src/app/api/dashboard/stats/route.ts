import { NextResponse } from 'next/server';
import { apiClient } from '@/utils/api-client';

export async function GET() {
  try {
    // Get dashboard stats from FastAPI
    const dashboardResponse = await apiClient.getDashboard();
    
    // Get recent users and payments for activity feed
    const [usersResponse, paymentsResponse] = await Promise.all([
      apiClient.getUsers({ limit: 5 }).catch(() => ({ success: false, data: { users: [] } })),
      apiClient.getPayments({ limit: 5 }).catch(() => ({ success: false, data: { payments: [] } }))
    ]);

    // Use real data from FastAPI
    const stats = dashboardResponse?.data || {
      total_users: 0,
      active_users: 0,
      inactive_users: 0,
      total_revenue: 0,
      payments_today: 0
    };

    // Extract users array from response - API returns { users: [...], pagination: {...} }
    const users = (usersResponse?.data?.users || []).map((user: any) => ({
      ...user,
      is_premium: user.subscription_active === 1 || user.subscription_active === true
    }));

    // Extract payments array from response - API returns { payments: [...], pagination: {...} }
    const payments = paymentsResponse?.data?.payments || [];

    // Format payments to include username (already has first_name, last_name from JOIN)
    const formattedPayments = payments.map((payment: any) => ({
      ...payment,
      username: payment.first_name 
        ? `${payment.first_name}${payment.last_name ? ' ' + payment.last_name : ''}`
        : payment.telegram_id ? `ID: ${payment.telegram_id}` : 'Невідомо'
    }));

    return NextResponse.json({
      success: true,
      data: {
        stats,
        recent_activity: {
          users,
          payments: formattedPayments
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
