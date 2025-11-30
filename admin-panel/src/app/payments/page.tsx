'use client';

import { useState, useEffect } from 'react';
import { 
  CreditCardIcon,
  BanknotesIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  EyeIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';
import ViewModal from '@/components/ViewModal';
import Pagination from '@/components/Pagination';

interface Payment {
  id: number;
  user_id: number;
  amount: number;
  currency: string;
  status: string;
  stripe_payment_intent_id?: string;
  stripe_invoice_id?: string;
  stripe_response_log?: string;
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
  const [statusFilter, setStatusFilter] = useState('');
  
  // Additional filter states
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  
  // Modal states
  const [showViewModal, setShowViewModal] = useState(false);
  const [showLogModal, setShowLogModal] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);

  useEffect(() => {
    fetchPayments();
  }, [currentPage, itemsPerPage, statusFilter, dateFrom, dateTo]);

  const fetchPayments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Отримуємо токен з localStorage або cookie
      const token = localStorage.getItem('auth_token');
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // Формуємо URL з параметрами фільтрації
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: itemsPerPage.toString(),
      });
      
      if (searchTerm) params.append('search', searchTerm);
      if (statusFilter) params.append('status', statusFilter);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      
      const response = await fetch(`/api/payments?${params.toString()}`, {
        headers,
      });
      
      if (response.ok) {
        const data = await response.json();
        const paymentsData = data.data || [];
        setPayments(paymentsData);
        setTotalItems(data.total || 0);
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
    // Статистика з поточних даних на сторінці (пагінація)
    // amount в центах, конвертуємо в євро
    const totalAmount = paymentsData
      .filter(p => p.status === 'completed' || p.status === 'succeeded')
      .reduce((sum, p) => sum + (p.amount / 100), 0);  // Конвертуємо центи в євро
    
    const totalCount = paymentsData.length; // Кількість на поточній сторінці
    const completedCount = paymentsData.filter(p => p.status === 'completed' || p.status === 'succeeded').length;
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
      payment.stripe_payment_intent_id?.includes(searchTerm) ||
      payment.amount.toString().includes(searchTerm);
    
    const matchesStatus = statusFilter === 'all' || payment.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const filteredSum = filteredPayments
    .filter(p => p.status === 'completed' || p.status === 'succeeded')
    .reduce((sum, p) => sum + (p.amount / 100), 0);  // Конвертуємо центи в євро

  const exportToExcel = async () => {
    try {
      const response = await fetch('/api/payments/export', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payments_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        throw new Error('Помилка експорту');
      }
    } catch (err) {
      console.error('Error exporting payments:', err);
      alert('Помилка експорту платежів');
    }
  };

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
      case 'completed':
      case 'succeeded':
        return 'Успішно';
      case 'pending': return 'В обробці';
      case 'failed': return 'Помилка';
      default: return status;
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed':
      case 'succeeded':
        return 'admin-status--success';
      case 'pending':
      case 'processing':
        return 'admin-status--pending';
      case 'failed':
        return 'admin-status--neutral';
      default:
        return 'admin-status--neutral';
    }
  };

  const handleViewPayment = (payment: Payment) => {
    setSelectedPayment(payment);
    setShowViewModal(true);
  };
  
  const handleViewLog = (payment: Payment) => {
    setSelectedPayment(payment);
    setShowLogModal(true);
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading">
          <div className="admin-loading__spinner"></div>
          <p className="admin-loading__text">Завантаження платежів...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="admin-alert admin-alert--danger">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header admin-page__header--with-actions">
        <div className="admin-page__title-section">
          <h1 className="admin-page__title">Платежі</h1>
          <p className="admin-page__subtitle">Управління платежами та транзакціями</p>
        </div>
        <button
          onClick={exportToExcel}
          className="admin-btn admin-btn--secondary"
        >
          <ArrowDownTrayIcon className="w-5 h-5" />
          Експорт в Excel
        </button>
      </div>

      {/* Stats Cards */}
      <div className="admin-stats">
        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Загальна сума</span>
            <BanknotesIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">€{stats.totalAmount.toFixed(2)}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Всього платежів</span>
            <CreditCardIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{stats.totalCount}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Успішні</span>
            <CheckCircleIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{stats.completedCount}</div>
          </div>
        </div>

        <div className="admin-stats__card">
          <div className="admin-stats__header">
            <span className="admin-stats__title">Проблемні</span>
            <ClockIcon className="admin-stats__icon" />
          </div>
          <div className="admin-stats__content">
            <div className="admin-stats__value">{stats.pendingCount + stats.failedCount}</div>
          </div>
        </div>
      </div>

      {/* Payments Table */}
      <div className="admin-table-container">
        <div className="admin-card__header">
          <h3 className="admin-card__title">Список платежів</h3>
          <p className="admin-card__subtitle">
            Знайдено: {filteredPayments.length} з {payments.length} платежів
            {filteredPayments.length > 0 && (
              <span className="ml-2">• Сума: €{filteredSum.toFixed(2)}</span>
            )}
          </p>
        </div>

        {/* Filters */}
        <div className="admin-filters" style={{ marginBottom: '1.5rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-base)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            {/* Search */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Пошук
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && fetchPayments()}
                  placeholder="Користувач, ID платежу..."
                  style={{
                    width: '100%',
                    padding: '0.5rem 2.5rem 0.5rem 0.75rem',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.875rem'
                  }}
                />
                <MagnifyingGlassIcon 
                  style={{ 
                    position: 'absolute', 
                    right: '0.75rem', 
                    top: '50%', 
                    transform: 'translateY(-50%)', 
                    width: '1.25rem', 
                    height: '1.25rem',
                    color: 'var(--text-tertiary)',
                    pointerEvents: 'none'
                  }} 
                />
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Статус платежу
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem',
                  background: 'var(--bg-primary)'
                }}
              >
                <option value="">Всі</option>
                <option value="succeeded">Успішно</option>
                <option value="pending">В очікуванні</option>
                <option value="failed">Не вдалося</option>
              </select>
            </div>

            {/* Date From */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Дата платежу від
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem'
                }}
              />
            </div>

            {/* Date To */}
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                Дата платежу до
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem'
                }}
              />
            </div>
          </div>

          {/* Filter Actions */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={fetchPayments}
              className="admin-btn admin-btn--primary admin-btn--sm"
            >
              <MagnifyingGlassIcon className="w-4 h-4" />
              Застосувати фільтри
            </button>
            <button
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('');
                setDateFrom('');
                setDateTo('');
                setCurrentPage(1);
              }}
              className="admin-btn admin-btn--secondary admin-btn--sm"
            >
              <XCircleIcon className="w-4 h-4" />
              Очистити
            </button>
          </div>
        </div>

        {filteredPayments.length > 0 ? (
          <>
          <div className="admin-table-wrapper">
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
              <tbody className="admin-table__body">
                {filteredPayments.map((payment) => (
                <tr key={payment.id} className="admin-table__row">
                  <td className="admin-table__cell admin-table__cell--bold">{payment.id}</td>
                  <td className="admin-table__cell">{payment.user_id}</td>
                  <td className="admin-table__cell admin-table__cell--bold">€{(payment.amount / 100).toFixed(2)}</td>
                  <td className="admin-table__cell">{payment.currency.toUpperCase()}</td>
                    <td className="admin-table__cell">
                      <span className={`admin-status ${getStatusClass(payment.status)}`}>
                        {getStatusText(payment.status)}
                      </span>
                    </td>
                    <td className="admin-table__cell">
                      {payment.stripe_invoice_id ? (
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {payment.stripe_invoice_id.substring(0, 20)}...
                        </code>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="admin-table__cell">
                      {new Date(payment.created_at).toLocaleString('uk-UA')}
                    </td>
                    <td className="admin-table__cell admin-table__cell--center">
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                        <button 
                          className="admin-btn admin-btn--sm admin-btn--secondary"
                          title="Переглянути деталі"
                          onClick={() => handleViewPayment(payment)}
                        >
                          <EyeIcon className="w-4 h-4" />
                        </button>
                        {payment.stripe_response_log && (
                          <button 
                            className="admin-btn admin-btn--sm admin-btn--primary"
                            title="Переглянути лог Stripe"
                            onClick={() => handleViewLog(payment)}
                          >
                            Лог
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          </div>          {!loading && (
            <Pagination
              currentPage={currentPage}
              totalPages={Math.ceil(totalItems / itemsPerPage)}
              totalItems={totalItems}
              itemsPerPage={itemsPerPage}
              onPageChange={setCurrentPage}
              onItemsPerPageChange={(items) => {
                setItemsPerPage(items);
                setCurrentPage(1);
              }}
            />
          )}
          </>
        ) : (
          <div className="admin-table__empty">
            <CreditCardIcon className="admin-table__empty-icon" />
            <p className="admin-table__empty-text">
              {searchTerm || statusFilter !== 'all' 
                ? 'Платежів за запитом не знайдено' 
                : 'Платежі відсутні'
              }
            </p>
          </div>
        )}
      </div>

      {/* View Modal */}
      {selectedPayment && (
        <ViewModal
          isOpen={showViewModal}
          onClose={() => {
            setShowViewModal(false);
            setSelectedPayment(null);
          }}
          title="Деталі платежу"
          fields={[
            { label: 'ID платежу', value: selectedPayment.id },
            { label: 'User ID', value: selectedPayment.user_id },
            { label: 'Сума', value: `€${(selectedPayment.amount / 100).toFixed(2)}` },
            { label: 'Валюта', value: selectedPayment.currency.toUpperCase() },
            { label: 'Статус', value: getStatusText(selectedPayment.status), type: 'status' },
            { label: 'Stripe Invoice ID', value: selectedPayment.stripe_invoice_id || '—' },
            { label: 'Stripe Payment ID', value: selectedPayment.stripe_payment_intent_id || '—' },
            { label: 'Дата створення', value: selectedPayment.created_at, type: 'date' },
            { label: 'Дата оновлення', value: selectedPayment.updated_at, type: 'date' },
          ]}
        />
      )}
      
      {/* Stripe Log Modal */}
      {selectedPayment && showLogModal && (
        <div className="admin-modal" style={{ zIndex: 999 }} onClick={() => setShowLogModal(false)}>
          <div className="admin-modal__backdrop" />
          <div className="admin-modal__content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
            <div className="admin-modal__header">
              <h2 className="admin-modal__title">Stripe Response Log</h2>
              <button 
                className="admin-modal__close"
                onClick={() => setShowLogModal(false)}
                aria-label="Закрити"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="admin-modal__body">
              <div style={{ 
                background: '#1e1e1e', 
                color: '#d4d4d4', 
                padding: '16px', 
                borderRadius: '8px',
                overflowX: 'auto',
                maxHeight: '500px',
                fontFamily: 'Monaco, Consolas, monospace',
                fontSize: '12px',
                lineHeight: '1.5'
              }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {selectedPayment.stripe_response_log ? 
                    JSON.stringify(JSON.parse(selectedPayment.stripe_response_log), null, 2) 
                    : 'Лог відсутній'}
                </pre>
              </div>
            </div>
            <div className="admin-modal__actions">
              <button 
                className="admin-btn admin-btn--secondary"
                onClick={() => setShowLogModal(false)}
              >
                Закрити
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}