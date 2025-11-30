import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET() {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth_token')?.value;
    
    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Unauthorized'
      }, { status: 401 });
    }

    const API_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';
    
    // Get dashboard stats from FastAPI
    const dashboardResponse = await fetch(`${API_URL}/api/dashboard`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!dashboardResponse.ok) {
      throw new Error('Failed to fetch dashboard data');
    }
    
    const dashboardData = await dashboardResponse.json();
    
    // Get recent users and payments for activity feed
    const [usersResponse, paymentsResponse] = await Promise.all([
      fetch(`${API_URL}/api/users?limit=5`, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      }).then(r => r.ok ? r.json() : { data: [] }).catch(() => ({ data: [] })),
      fetch(`${API_URL}/api/payments?limit=5`, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      }).then(r => r.ok ? r.json() : { data: [] }).catch(() => ({ data: [] }))
    ]);

    // Use real data from FastAPI
    const stats = dashboardData || {
      total_users: 0,
      active_users: 0,
      inactive_users: 0,
      total_revenue: 0,
      payments_today: 0
    };

    // Extract users array from response (API returns { data: [...], total: N, pagination: {...} })
    const users = (usersResponse?.data || []).map((user: any) => ({
      ...user,
      is_premium: user.subscription_active === 1 || user.subscription_active === true
    }));

    // Extract payments array from response (API returns { data: [...], total: N, pagination: {...} })
    const payments = paymentsResponse?.data || [];

    // Format payments to include username
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
