'use client';

import { useState, useEffect } from 'react';
import { 
  UsersIcon,
  CreditCardIcon,
  CheckBadgeIcon,
  BanknotesIcon
} from '@heroicons/react/24/outline';

interface DashboardStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  total_revenue: number;
  payments_today: number;
}

interface RecentUser {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  created_at: string;
  is_premium?: boolean;
}

interface RecentPayment {
  id: number;
  amount: number;
  status: string;
  created_at: string;
  username?: string;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    total_users: 0,
    active_users: 0,
    inactive_users: 0,
    total_revenue: 0,
    payments_today: 0
  });
  const [recentUsers, setRecentUsers] = useState<RecentUser[]>([]);
  const [recentPayments, setRecentPayments] = useState<RecentPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch dashboard stats
      const statsResponse = await fetch('/api/dashboard/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        if (statsData.success) {
          setStats(statsData.data.stats);
          setRecentUsers(statsData.data.recent_activity.users || []);
          setRecentPayments(statsData.data.recent_activity.payments || []);
        }
      } else {
        throw new Error('Failed to fetch dashboard data');
      }

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Помилка завантаження даних');
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      title: 'Всього користувачів',
      value: stats.total_users.toLocaleString(),
      icon: UsersIcon,
      change: `${stats.active_users + stats.inactive_users} зареєстровано`,
      changeType: 'positive' as const
    },
    {
      title: 'Активні користувачі',
      value: stats.active_users.toLocaleString(),
      icon: CheckBadgeIcon,
      change: `${Math.round((stats.active_users / stats.total_users) * 100 || 0)}% активних`,
      changeType: 'positive' as const
    },
    {
      title: 'Не активні користувачі',
      value: stats.inactive_users.toLocaleString(),
      icon: UsersIcon,
      change: `${Math.round((stats.inactive_users / stats.total_users) * 100 || 0)}% не активних`,
      changeType: 'neutral' as const
    },
    {
      title: 'Загальний дохід',
      value: `€${(stats.total_revenue / 100).toFixed(2)}`,
      icon: CreditCardIcon,
      change: 'Успішні платежі',
      changeType: 'positive' as const
    },
    {
      title: 'Сьогодні платежів',
      value: stats.payments_today.toLocaleString(),
      icon: BanknotesIcon,
      change: 'За сьогодні',
      changeType: 'positive' as const
    }
  ];

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading">
          <div className="admin-loading__spinner"></div>
          <p className="admin-loading__text">Завантаження...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="admin-alert admin-alert--danger" style={{marginBottom: 'var(--spacing-base)'}}>
          {error}
        </div>
        <button 
          onClick={fetchDashboardData}
          className="admin-btn admin-btn--primary"
        >
          Спробувати знову
        </button>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <h1 className="admin-page__title">Дашборд</h1>
        <p className="admin-page__subtitle">
          Огляд статистики та основних метрик
        </p>
      </div>

      <div className="dashboard-stats">
        {statCards.map((stat, index) => (
          <div key={index} className="dashboard-stats__card">
            <div className="dashboard-stats__header">
              <div className="dashboard-stats__title">
                {stat.title}
              </div>
              <stat.icon className="dashboard-stats__icon" />
            </div>
            
            <div className="dashboard-stats__content">
              <div className="dashboard-stats__value">
                {stat.value}
              </div>
              <div className={`dashboard-stats__change dashboard-stats__change--${stat.changeType}`}>
                {stat.change}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="dashboard-activity">
        {/* Recent Users */}
        <div className="dashboard-activity__section">
          <div className="dashboard-activity__header">
            <h3 className="dashboard-activity__title">Нові користувачі</h3>
          </div>
          <div className="dashboard-activity__content">
            {recentUsers.length > 0 ? (
              <div className="dashboard-activity__list">
                {recentUsers.map((user) => (
                  <div key={user.id} className="dashboard-activity__item">
                    <div className="dashboard-activity__item-info">
                      <div className="dashboard-activity__item-name">
                        {user.first_name} {user.last_name}
                      </div>
                      {user.username && (
                        <div className="dashboard-activity__item-username">
                          @{user.username}
                        </div>
                      )}
                      <div className="dashboard-activity__item-date">
                        {new Date(user.created_at).toLocaleDateString('uk-UA')}
                      </div>
                    </div>
                    <div className="dashboard-activity__item-status">
                      {user.is_premium && (
                        <span className="admin-status admin-status--success">
                          Активна підписка
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="dashboard-activity__empty">
                Немає нових користувачів
              </div>
            )}
          </div>
        </div>

        {/* Recent Payments */}
        <div className="dashboard-activity__section">
          <div className="dashboard-activity__header">
            <h3 className="dashboard-activity__title">Останні платежі</h3>
          </div>
          <div className="dashboard-activity__content">
            {recentPayments.length > 0 ? (
              <div className="dashboard-activity__list">
                {recentPayments.map((payment) => (
                  <div key={payment.id} className="dashboard-activity__item">
                    <div className="dashboard-activity__item-info">
                      <div className="dashboard-activity__item-amount">
                        €{(payment.amount / 100).toFixed(2)}
                      </div>
                      {payment.username && (
                        <div className="dashboard-activity__item-username">
                          {payment.username}
                        </div>
                      )}
                      <div className="dashboard-activity__item-date">
                        {new Date(payment.created_at).toLocaleDateString('uk-UA')}
                      </div>
                    </div>
                    <div className="dashboard-activity__item-status">
                      <span className={`admin-status ${
                        payment.status === 'completed' || payment.status === 'succeeded' 
                          ? 'admin-status--success' 
                          : payment.status === 'pending' || payment.status === 'processing'
                          ? 'admin-status--pending'
                          : 'admin-status--failed'
                      }`}>
                        {payment.status === 'succeeded' ? 'Успішно' : 
                         payment.status === 'completed' ? 'Завершено' :
                         payment.status === 'pending' ? 'В очікуванні' :
                         payment.status === 'processing' ? 'Обробляється' :
                         'Не вдалося'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="dashboard-activity__empty">
                Немає останніх платежів
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}