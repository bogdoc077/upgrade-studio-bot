'use client';

import { useState, useEffect } from 'react';
import './logs.css';

type ServiceType = 'bot' | 'api' | 'webhook' | 'admin' | 'system';

interface LogsData {
  success: boolean;
  service: string;
  logs: string[];
  total_lines: number;
  file_path?: string;
  message?: string;
}

interface SystemLog {
  id: number;
  task_type: string;
  status: string;
  message: string | null;
  details: any;
  duration_ms: number | null;
  created_at: string;
}

interface SystemLogsData {
  data: SystemLog[];
  total: number;
  stats: any[];
  pagination: {
    current_page: number;
    total_pages: number;
    total_logs: number;
    per_page: number;
  };
}

export default function SystemLogs() {
  const [activeTab, setActiveTab] = useState<ServiceType>('system');
  const [logsData, setLogsData] = useState<LogsData | null>(null);
  const [systemLogsData, setSystemLogsData] = useState<SystemLogsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lines, setLines] = useState(100);
  const [page, setPage] = useState(1);

  const services = [
    { id: 'system' as ServiceType, name: 'Автоматичні задачі' },
    { id: 'bot' as ServiceType, name: 'Telegram Bot' },
    { id: 'api' as ServiceType, name: 'API Server' },
    { id: 'webhook' as ServiceType, name: 'Webhook Server' },
    { id: 'admin' as ServiceType, name: 'Admin Panel' }
  ];

  const fetchLogs = async (service: ServiceType) => {
    try {
      setLoading(true);
      setError(null);

      if (service === 'system') {
        // Завантажуємо системні логи
        const response = await fetch(`/api/system-logs?page=${page}&limit=50`);
        if (!response.ok) {
          throw new Error('Failed to fetch system logs');
        }
        const data = await response.json();
        setSystemLogsData(data);
        setLogsData(null);
      } else {
        // Завантажуємо звичайні логи
        const response = await fetch(`/api/logs?service=${service}&lines=${lines}`);
        if (!response.ok) {
          throw new Error('Failed to fetch logs');
        }
        const data = await response.json();
        setLogsData(data);
        setSystemLogsData(null);
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
      setError('Помилка завантаження логів');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(activeTab);
  }, [activeTab, lines, page]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchLogs(activeTab);
      }, 5000); // Оновлюємо кожні 5 секунд

      return () => clearInterval(interval);
    }
  }, [autoRefresh, activeTab]);

  const handleTabChange = (service: ServiceType) => {
    setActiveTab(service);
  };

  const handleRefresh = () => {
    fetchLogs(activeTab);
  };

  const handleDownload = () => {
    if (!logsData?.logs) return;

    const blob = new Blob([logsData.logs.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeTab}-logs-${new Date().toISOString()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <h1 className="admin-page__title">Логи системи</h1>
        <p className="admin-page__subtitle">
          Перегляд логів всіх сервісів системи
        </p>
      </div>

      {/* Tabs */}
      <div className="logs-tabs">
        {services.map((service) => (
          <button
            key={service.id}
            className={`logs-tabs__tab ${activeTab === service.id ? 'logs-tabs__tab--active' : ''}`}
            onClick={() => handleTabChange(service.id)}
          >
            <span className="logs-tabs__name">{service.name}</span>
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="logs-controls">
        <div className="logs-controls__left">
          <label className="logs-controls__label">
            Рядків:
            <select 
              value={lines} 
              onChange={(e) => setLines(Number(e.target.value))}
              className="logs-controls__select"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
              <option value={1000}>1000</option>
            </select>
          </label>

          <label className="logs-controls__checkbox">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Авто-оновлення (5 сек)</span>
          </label>
        </div>

        <div className="logs-controls__right">
          <button 
            onClick={handleRefresh}
            className="admin-btn admin-btn--secondary"
            disabled={loading}
          >
            Оновити
          </button>
          <button 
            onClick={handleDownload}
            className="admin-btn admin-btn--secondary"
            disabled={!logsData?.logs || logsData.logs.length === 0}
          >
            Завантажити
          </button>
        </div>
      </div>

      {/* Logs Display */}
      <div className="logs-container">
        {loading && !logsData && !systemLogsData ? (
          <div className="logs-loading">
            <div className="admin-loading__spinner"></div>
            <p>Завантаження логів...</p>
          </div>
        ) : error ? (
          <div className="logs-error">
            <p>{error}</p>
            <button onClick={handleRefresh} className="admin-btn admin-btn--primary">
              Спробувати знову
            </button>
          </div>
        ) : activeTab === 'system' && systemLogsData ? (
          <div className="system-logs">
            {/* Інформація про розклад задач */}
            <div className="system-logs__schedule">
              <h3>📅 Розклад автоматичних задач</h3>
              <div className="schedule-grid">
                <div className="schedule-item">
                  <div className="schedule-item__icon">⏰</div>
                  <div className="schedule-item__content">
                    <h4>process_reminders</h4>
                    <p className="schedule-time">Кожну хвилину</p>
                    <p className="schedule-desc">Обробка та надсилання нагадувань користувачам</p>
                  </div>
                </div>
                
                <div className="schedule-item">
                  <div className="schedule-item__icon">💳</div>
                  <div className="schedule-item__content">
                    <h4>process_payment_events</h4>
                    <p className="schedule-time">Кожні 10 секунд</p>
                    <p className="schedule-desc">Обробка подій успішних оплат</p>
                  </div>
                </div>
                
                <div className="schedule-item">
                  <div className="schedule-item__icon">📢</div>
                  <div className="schedule-item__content">
                    <h4>process_broadcasts</h4>
                    <p className="schedule-time">Кожні 30 секунд</p>
                    <p className="schedule-desc">Обробка та відправка розсилок</p>
                  </div>
                </div>
                
                <div className="schedule-item">
                  <div className="schedule-item__icon">🔍</div>
                  <div className="schedule-item__content">
                    <h4>check_expired_subscriptions</h4>
                    <p className="schedule-time">Щодня о 01:00</p>
                    <p className="schedule-desc">Перевірка та деактивація закінчених підписок</p>
                  </div>
                </div>
                
                <div className="schedule-item">
                  <div className="schedule-item__icon">🧹</div>
                  <div className="schedule-item__content">
                    <h4>cleanup_old_reminders</h4>
                    <p className="schedule-time">Щодня о 02:00</p>
                    <p className="schedule-desc">Видалення старих неактивних нагадувань (&gt;30 днів)</p>
                  </div>
                </div>
                
                <div className="schedule-item">
                  <div className="schedule-item__icon">🔔</div>
                  <div className="schedule-item__content">
                    <h4>schedule_subscription_reminders</h4>
                    <p className="schedule-time">Щодня о 10:00</p>
                    <p className="schedule-desc">Планування нагадувань про продовження підписок</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Статистика задач */}
            {systemLogsData.stats && systemLogsData.stats.length > 0 && (
              <div className="system-logs__stats">
                <h3>Статистика за 24 години</h3>
                <div className="stats-grid">
                  {systemLogsData.stats.map((stat) => (
                    <div key={stat.task_type} className="stat-card">
                      <h4>{stat.task_type}</h4>
                      <div className="stat-metrics">
                        <span>Всього: {stat.total}</span>
                        <span className="stat-success">Успішно: {stat.completed}</span>
                        <span className="stat-error">Помилок: {stat.failed}</span>
                        {stat.avg_duration_ms && (
                          <span>Сер. час: {Math.round(stat.avg_duration_ms)}ms</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Таблиця логів */}
            <div className="system-logs__table">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Час</th>
                    <th>Задача</th>
                    <th>Статус</th>
                    <th>Повідомлення</th>
                    <th>Деталі</th>
                    <th>Тривалість</th>
                  </tr>
                </thead>
                <tbody>
                  {systemLogsData.data.map((log) => (
                    <tr key={log.id}>
                      <td>{new Date(log.created_at).toLocaleString('uk-UA')}</td>
                      <td><code>{log.task_type}</code></td>
                      <td>
                        <span className={`admin-status admin-status--${
                          log.status === 'completed' ? 'active' : 
                          log.status === 'failed' ? 'inactive' : 
                          'warning'
                        }`}>
                          {log.status}
                        </span>
                      </td>
                      <td>{log.message}</td>
                      <td>
                        {log.details && (
                          <details>
                            <summary>Показати</summary>
                            <pre>{JSON.stringify(log.details, null, 2)}</pre>
                          </details>
                        )}
                      </td>
                      <td>{log.duration_ms ? `${log.duration_ms}ms` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Пагінація */}
            {systemLogsData.pagination.total_pages > 1 && (
              <div className="admin-pagination">
                <button
                  className="admin-pagination__btn"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  ← Назад
                </button>
                <span className="admin-pagination__info">
                  Сторінка {page} з {systemLogsData.pagination.total_pages}
                </span>
                <button
                  className="admin-pagination__btn"
                  onClick={() => setPage(p => Math.min(systemLogsData.pagination.total_pages, p + 1))}
                  disabled={page === systemLogsData.pagination.total_pages}
                >
                  Вперед →
                </button>
              </div>
            )}
          </div>
        ) : logsData?.logs && logsData.logs.length > 0 ? (
          <>
            <div className="logs-info">
              <span>Відображено рядків: {logsData.total_lines}</span>
              {logsData.file_path && (
                <span className="logs-info__path">Файл: {logsData.file_path}</span>
              )}
            </div>
            <pre className="logs-content">
              {logsData.logs.map((line, index) => (
                <div key={index} className="logs-line">
                  <span className="logs-line__number">{index + 1}</span>
                  <span className="logs-line__text">{line}</span>
                </div>
              ))}
            </pre>
          </>
        ) : (
          <div className="logs-empty">
            <p>{logsData?.message || 'Логи відсутні'}</p>
          </div>
        )}
      </div>
    </div>
  );
}
