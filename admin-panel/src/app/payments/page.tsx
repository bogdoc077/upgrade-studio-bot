'use client';

import { useState, useEffect } from 'react';
import { 
  CreditCardIcon,
  BanknotesIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
  EyeIcon
} from '@heroicons/react/24/outline';

interface Payment {
  id: number;
  user_id: number;
  amount: number;
  currency: string;
  status: string;
  stripe_payment_id?: string;
  created_at: string;
  updated_at: string;
}

interface PaymentStats {
  totalAmount: number;
  totalCount: number;
  completedCount: number;
  pendingCount: number;
  failedCount: number;
}

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [stats, setStats] = useState<PaymentStats>({
    totalAmount: 0,
    totalCount: 0,
    completedCount: 0,
    pendingCount: 0,
    failedCount: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/payments');
      if (response.ok) {
        const data = await response.json();
        const paymentsData = data.data || [];
        setPayments(paymentsData);
        calculateStats(paymentsData);
      } else {
        throw new Error('Помилка завантаження платежів');
      }
    } catch (err) {
      console.error('Error fetching payments:', err);
      setError('Помилка завантаження платежів');
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (paymentsData: Payment[]) => {
    const totalAmount = paymentsData
      .filter(p => p.status === 'completed')
      .reduce((sum, p) => sum + p.amount, 0);
    
    const totalCount = paymentsData.length;
    const completedCount = paymentsData.filter(p => p.status === 'completed').length;
    const pendingCount = paymentsData.filter(p => p.status === 'pending').length;
    const failedCount = paymentsData.filter(p => p.status === 'failed').length;

    setStats({
      totalAmount,
      totalCount,
      completedCount,
      pendingCount,
      failedCount
    });
  };

  const filteredPayments = payments.filter(payment => {
    const matchesSearch = 
      payment.id.toString().includes(searchTerm) ||
      payment.user_id.toString().includes(searchTerm) ||
      payment.stripe_payment_id?.includes(searchTerm) ||
      payment.amount.toString().includes(searchTerm);
    
    const matchesStatus = statusFilter === 'all' || payment.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleIcon className="w-4 h-4 text-green-500" />;
      case 'pending': return <ClockIcon className="w-4 h-4 text-yellow-500" />;
      case 'failed': return <XCircleIcon className="w-4 h-4 text-red-500" />;
      default: return <ClockIcon className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'Успішно';
      case 'pending': return 'В обробці';
      case 'failed': return 'Помилка';
      default: return status;
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed': return 'admin-status--active';
      case 'pending': return 'admin-status--pending';
      case 'failed': return 'admin-status--error';
      default: return 'admin-status--inactive';
    }
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-flex admin-flex--center" style={{ minHeight: '400px' }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Завантаження платежів...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="admin-flex admin-flex--center" style={{ minHeight: '400px' }}>
          <div className="text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <button 
              onClick={fetchPayments}
              className="admin-btn admin-btn--primary"
            >
              Спробувати знову
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header">
        <h1 className="admin-page__title">Платежі</h1>
        <p className="admin-page__subtitle">
          Управління транзакціями та платежами користувачів
        </p>
        <div className="admin-page__actions">
          <div className="admin-form__group" style={{ marginBottom: 0, minWidth: '200px' }}>
            <input
              type="text"
              placeholder="Пошук платежів..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="admin-form__input"
            />
          </div>
          <div className="admin-form__group" style={{ marginBottom: 0, minWidth: '150px' }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="admin-form__select"
            >
              <option value="all">Всі статуси</option>
              <option value="completed">Успішні</option>
              <option value="pending">В обробці</option>
              <option value="failed">Помилка</option>
            </select>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">€{stats.totalAmount.toFixed(2)}</div>
                <div className="text-sm text-gray-500">Загальна сума</div>
              </div>
              <BanknotesIcon className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{stats.totalCount}</div>
                <div className="text-sm text-gray-500">Всього платежів</div>
              </div>
              <CreditCardIcon className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{stats.completedCount}</div>
                <div className="text-sm text-gray-500">Успішні</div>
              </div>
              <CheckCircleIcon className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card__body">
            <div className="admin-flex admin-flex--between">
              <div>
                <div className="text-2xl font-bold text-gray-900">{stats.pendingCount + stats.failedCount}</div>
                <div className="text-sm text-gray-500">Проблемні</div>
              </div>
              <ClockIcon className="w-8 h-8 text-yellow-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Payments Table */}
      <div className="admin-card">
        <div className="admin-card__header">
          <h3 className="admin-card__title">Список платежів</h3>
          <p className="admin-card__subtitle">
            Знайдено: {filteredPayments.length} з {payments.length} платежів
          </p>
        </div>
        <div className="admin-card__body admin-content--no-padding">
          {filteredPayments.length > 0 ? (
            <table className="admin-table">
              <thead className="admin-table__header">
                <tr>
                  <th className="admin-table__header-cell">ID</th>
                  <th className="admin-table__header-cell">User ID</th>
                  <th className="admin-table__header-cell">Сума</th>
                  <th className="admin-table__header-cell">Валюта</th>
                  <th className="admin-table__header-cell">Статус</th>
                  <th className="admin-table__header-cell">Stripe ID</th>
                  <th className="admin-table__header-cell">Дата створення</th>
                  <th className="admin-table__header-cell admin-table__header-cell--center">Дії</th>
                </tr>
              </thead>
              <tbody>
                {filteredPayments.map((payment) => (
                  <tr key={payment.id} className="admin-table__row">
                    <td className="admin-table__cell font-medium">{payment.id}</td>
                    <td className="admin-table__cell">{payment.user_id}</td>
                    <td className="admin-table__cell font-medium">{payment.amount}</td>
                    <td className="admin-table__cell">{payment.currency.toUpperCase()}</td>
                    <td className="admin-table__cell">
                      <div className="admin-flex admin-gap--sm">
                        {getStatusIcon(payment.status)}
                        <span className={`admin-status ${getStatusClass(payment.status)}`}>
                          {getStatusText(payment.status)}
                        </span>
                      </div>
                    </td>
                    <td className="admin-table__cell">
                      {payment.stripe_payment_id ? (
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {payment.stripe_payment_id.substring(0, 20)}...
                        </code>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="admin-table__cell">
                      {new Date(payment.created_at).toLocaleString('uk-UA')}
                    </td>
                    <td className="admin-table__cell admin-table__cell--center">
                      <button 
                        className="admin-btn admin-btn--small admin-btn--secondary"
                        title="Переглянути деталі"
                      >
                        <EyeIcon className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">
                {searchTerm || statusFilter !== 'all' 
                  ? 'Платежів за запитом не знайдено' 
                  : 'Платежі відсутні'
                }
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}