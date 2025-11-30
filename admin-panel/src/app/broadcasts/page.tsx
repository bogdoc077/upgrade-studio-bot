'use client';

import { useState, useEffect } from 'react';
import { 
  SpeakerWaveIcon,
  PlusIcon,
  PhotoIcon,
  DocumentIcon,
  LinkIcon
} from '@heroicons/react/24/outline';
import { makeApiCall } from '@/utils/api-client';
import MessageBuilder, { MessageBlock } from '@/components/MessageBuilder';
import Pagination from '@/components/Pagination';

interface BroadcastStats {
  active: number;
  inactive: number;
  no_payment: number;
}

interface Broadcast {
  id: number;
  target_group: string;
  title?: string;
  message_text: string;
  attachment_type?: string;
  attachment_url?: string;
  button_text?: string;
  button_url?: string;
  status: string;
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  created_at: string;
  created_by_username: string;
  error_log?: string;
  full_log?: string;
}

export default function BroadcastsPage() {
  const [stats, setStats] = useState<BroadcastStats | null>(null);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  
  // Form state
  const [targetGroup, setTargetGroup] = useState('active');
  const [title, setTitle] = useState('');
  const [messageBlocks, setMessageBlocks] = useState<MessageBlock[]>([]);
  const [creating, setCreating] = useState(false);
  
  // Detail modal state
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedBroadcast, setSelectedBroadcast] = useState<Broadcast | null>(null);
  
  // Error log modal state
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorLogContent, setErrorLogContent] = useState<string>('');
  
  // Full log modal state
  const [showFullLogModal, setShowFullLogModal] = useState(false);
  const [fullLogContent, setFullLogContent] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [currentPage, itemsPerPage]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, broadcastsData] = await Promise.all([
        makeApiCall('/api/broadcasts/stats', { method: 'GET' }),
        makeApiCall(`/api/broadcasts?page=${currentPage}&limit=${itemsPerPage}`, { method: 'GET' })
      ]);
      
      setStats(statsData);
      setBroadcasts(broadcastsData.broadcasts || []);
      setTotalItems(broadcastsData.total || 0);
    } catch (error) {
      console.error('Error loading broadcasts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File): Promise<{ url: string; type: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/broadcasts/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload file');
    }

    const data = await response.json();
    
    if (data.success) {
      // API може повертати дані або напряму, або в data.data
      const fileData = data.data || data;
      return { url: fileData.url, type: fileData.attachment_type };
    } else {
      throw new Error(data.error || 'Upload failed');
    }
  };

  const handleCreateBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (messageBlocks.length === 0) {
      alert('Додайте хоча б один елемент до повідомлення');
      return;
    }
    
    // Валідація блоків
    for (const block of messageBlocks) {
      if (block.type === 'text' && !block.content.trim()) {
        alert('Заповніть текстові поля');
        return;
      }
      if ((block.type === 'image' || block.type === 'video' || block.type === 'document') && !block.fileUrl) {
        alert('Завантажте всі файли');
        return;
      }
      if (block.type === 'button' && (!block.buttonText || !block.buttonUrl)) {
        alert('Заповніть текст та посилання для всіх кнопок');
        return;
      }
    }
    
    try {
      setCreating(true);
      
      // Збираємо дані з блоків
      const textBlocks = messageBlocks.filter(b => b.type === 'text');
      const imageBlocks = messageBlocks.filter(b => b.type === 'image');
      const videoBlocks = messageBlocks.filter(b => b.type === 'video');
      const documentBlocks = messageBlocks.filter(b => b.type === 'document');
      const buttonBlocks = messageBlocks.filter(b => b.type === 'button');
      
      // Підрахунок кількості повідомлень
      const mediaBlocks = [...imageBlocks, ...videoBlocks, ...documentBlocks];
      const messageCount = Math.max(1, mediaBlocks.length);
      
      // Інформація про структуру повідомлень
      let messageInfo = '';
      if (messageCount > 1) {
        messageInfo = `Буде відправлено ${messageCount} повідомлень:\n`;
        if (textBlocks.length > 0) {
          messageInfo += `• Повідомлення 1: Текст`;
          if (mediaBlocks[0]) {
            messageInfo += ` + ${mediaBlocks[0].type === 'image' ? 'Зображення' : mediaBlocks[0].type === 'video' ? 'Відео' : 'Документ'}`;
          }
          if (buttonBlocks[0]) {
            messageInfo += ` + Кнопка`;
          }
          messageInfo += '\n';
          for (let i = 1; i < mediaBlocks.length; i++) {
            const media = mediaBlocks[i];
            messageInfo += `• Повідомлення ${i + 1}: ${media.type === 'image' ? 'Зображення' : media.type === 'video' ? 'Відео' : 'Документ'}\n`;
          }
        } else {
          mediaBlocks.forEach((media, i) => {
            messageInfo += `• Повідомлення ${i + 1}: ${media.type === 'image' ? 'Зображення' : media.type === 'video' ? 'Відео' : 'Документ'}`;
            if (i === 0 && buttonBlocks[0]) messageInfo += ` + Кнопка`;
            messageInfo += '\n';
          });
        }
        
        const confirmed = window.confirm(messageInfo + '\nПродовжити?');
        if (!confirmed) {
          setCreating(false);
          return;
        }
      }
      
      // Зберігаємо всі блоки для бекенду
      const messageText = textBlocks.length > 0 ? textBlocks[0].content : null;
      const firstMedia = mediaBlocks[0];
      const firstButton = buttonBlocks[0];
      
      const data = {
        target_group: targetGroup,
        title: title || null,
        message_text: messageText,
        attachment_type: firstMedia ? firstMedia.type : null,
        attachment_url: firstMedia ? firstMedia.fileUrl : null,
        button_text: firstButton ? firstButton.buttonText : null,
        button_url: firstButton ? firstButton.buttonUrl : null,
        message_blocks: messageBlocks.map(block => ({
          type: block.type,
          content: block.content || '',
          fileUrl: block.fileUrl || null,
          buttonText: block.buttonText || null,
          buttonUrl: block.buttonUrl || null
        }))
      };
      
      console.log('Creating broadcast with data:', data);
      
      await makeApiCall('/api/broadcasts', {
        method: 'POST',
        body: JSON.stringify(data)
      });
      
      // Reset form
      setTitle('');
      setMessageBlocks([]);
      setShowCreateModal(false);
      
      // Reload data
      loadData();
    } catch (error: any) {
      alert('Помилка створення розсилки: ' + error.message);
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { text: string; className: string }> = {
      pending: { text: 'Очікує', className: 'admin-status--neutral' },
      processing: { text: 'Відправляється', className: 'admin-status--warning' },
      completed: { text: 'Завершено', className: 'admin-status--success' },
      failed: { text: 'Помилка', className: 'admin-status--failed' }
    };
    
    const { text, className } = statusMap[status] || statusMap.pending;
    return <span className={`admin-status ${className}`}>{text}</span>;
  };

  const getTargetGroupName = (group: string) => {
    const names: Record<string, string> = {
      active: 'Активні підписники',
      inactive: 'Неактивні користувачі',
      no_payment: 'Не оплатили'
    };
    return names[group] || group;
  };

  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header admin-page__header--with-actions">
        <div className="admin-page__title-section">
          <h1 className="admin-page__title">Розсилки</h1>
          <p className="admin-page__subtitle">Масові повідомлення користувачам</p>
        </div>
        <button 
          className="admin-btn admin-btn--primary"
          onClick={() => setShowCreateModal(true)}
        >
          <PlusIcon className="w-5 h-5" />
          Створити розсилку
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="admin-stats">
          <div className="admin-stats__card">
            <div className="admin-stats__header">
              <span className="admin-stats__title">Активні підписники</span>
            </div>
            <div className="admin-stats__content">
              <div className="admin-stats__value">{stats.active}</div>
            </div>
          </div>
          <div className="admin-stats__card">
            <div className="admin-stats__header">
              <span className="admin-stats__title">Неактивні користувачі</span>
            </div>
            <div className="admin-stats__content">
              <div className="admin-stats__value">{stats.inactive}</div>
            </div>
          </div>
          <div className="admin-stats__card">
            <div className="admin-stats__header">
              <span className="admin-stats__title">Не оплатили</span>
            </div>
            <div className="admin-stats__content">
              <div className="admin-stats__value">{stats.no_payment}</div>
            </div>
          </div>
        </div>
      )}

      {/* Broadcasts Table */}
      <div className="admin-table-container">
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead className="admin-table__header">
              <tr>
                <th className="admin-table__header-cell">Заголовок</th>
                <th className="admin-table__header-cell">Група</th>
                <th className="admin-table__header-cell">Статус</th>
                <th className="admin-table__header-cell">Отримувачі</th>
                <th className="admin-table__header-cell">Відправлено</th>
                <th className="admin-table__header-cell">Помилок</th>
                <th className="admin-table__header-cell">Створено</th>
                <th className="admin-table__header-cell admin-table__header-cell--actions">Дії</th>
              </tr>
            </thead>
            <tbody className="admin-table__body">
              {broadcasts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-table__empty">
                    <SpeakerWaveIcon className="admin-table__empty-icon" />
                    <p className="admin-table__empty-text">Розсилок ще немає</p>
                  </td>
                </tr>
              ) : (
                broadcasts.map(broadcast => (
                  <tr key={broadcast.id} className="admin-table__row">
                    <td className="admin-table__cell">
                      <div style={{fontWeight: 500}}>
                        {broadcast.title || `Розсилка #${broadcast.id}`}
                      </div>
                    </td>
                    <td className="admin-table__cell">
                      {getTargetGroupName(broadcast.target_group)}
                    </td>
                    <td className="admin-table__cell">
                      {getStatusBadge(broadcast.status)}
                    </td>
                    <td className="admin-table__cell">{broadcast.total_recipients}</td>
                    <td className="admin-table__cell" style={{color: 'var(--color-success)'}}>{broadcast.sent_count}</td>
                    <td className="admin-table__cell" style={{color: 'var(--color-danger)'}}>{broadcast.failed_count}</td>
                    <td className="admin-table__cell">
                      {new Date(broadcast.created_at).toLocaleDateString('uk-UA')}
                    </td>
                    <td className="admin-table__cell admin-table__cell--actions">
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => {
                            console.log('Selected broadcast:', broadcast);
                            setSelectedBroadcast(broadcast);
                            setShowDetailModal(true);
                          }}
                          className="admin-btn admin-btn--secondary admin-btn--sm"
                        >
                          Переглянути
                        </button>
                        {broadcast.full_log && (
                          <button
                            onClick={() => {
                              setFullLogContent(broadcast.full_log || '');
                              setShowFullLogModal(true);
                            }}
                            className="admin-btn admin-btn--primary admin-btn--sm"
                            title="Переглянути повний лог розсилки"
                          >
                            Лог
                          </button>
                        )}
                        {broadcast.failed_count > 0 && broadcast.error_log && (
                          <button
                            onClick={() => {
                              setErrorLogContent(broadcast.error_log || '');
                              setShowErrorModal(true);
                            }}
                            className="admin-btn admin-btn--danger admin-btn--sm"
                            title="Переглянути помилки"
                          >
                            Помилки ({broadcast.failed_count})
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {!loading && broadcasts.length > 0 && (
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
      </div>
      {/* Create Modal */}
      {showCreateModal && (
        <div className="admin-modal" onClick={() => !creating && setShowCreateModal(false)}>
          <div className="admin-modal__backdrop" />
          <div className="admin-modal__content admin-modal__content--lg" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal__header">
              <h2 className="admin-modal__title">Нова розсилка</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="admin-modal__close"
                type="button"
                title="Закрити"
                disabled={creating}
              >
                <span>✕</span>
              </button>
            </div>
            
            <form onSubmit={handleCreateBroadcast}>
              <div className="admin-modal__body">
                <div className="admin-form">
                  <div className="admin-form__group">
                    <label className="admin-form__label">Цільова група</label>
                    <select 
                      className="admin-form__select"
                      value={targetGroup}
                      onChange={(e) => setTargetGroup(e.target.value)}
                      required
                    >
                      <option value="active">Активні підписники ({stats?.active || 0})</option>
                      <option value="inactive">Неактивні користувачі ({stats?.inactive || 0})</option>
                      <option value="no_payment">Не оплатили ({stats?.no_payment || 0})</option>
                    </select>
                  </div>

                  <div className="admin-form__group">
                    <label className="admin-form__label">Заголовок (необов'язково)</label>
                    <input
                      type="text"
                      className="admin-form__input"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Заголовок для відображення в адмінці"
                    />
                  </div>

                  <div className="admin-form__group">
                    <label className="admin-form__label">Конструктор повідомлення</label>
                    <MessageBuilder 
                      blocks={messageBlocks}
                      onChange={setMessageBlocks}
                      onFileUpload={handleFileUpload}
                    />
                  </div>
                </div>
              </div>

              <div className="admin-modal__actions">
                <button
                  type="button"
                  className="admin-btn admin-btn--secondary"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creating}
                >
                  Скасувати
                </button>
                <button
                  type="submit"
                  className="admin-btn admin-btn--primary"
                  disabled={creating}
                >
                  {creating ? 'Створення...' : 'Створити розсилку'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedBroadcast && (
        <div className="admin-modal" onClick={() => setShowDetailModal(false)}>
          <div className="admin-modal__backdrop" />
          <div className="admin-modal__content" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal__header">
              <h2 className="admin-modal__title">
                {selectedBroadcast.title || `Розсилка #${selectedBroadcast.id}`}
              </h2>
              <button
                onClick={() => setShowDetailModal(false)}
                className="admin-modal__close"
                type="button"
                title="Закрити"
              >
                <span>✕</span>
              </button>
            </div>
            
            <div className="admin-modal__body">
              {(() => {
                console.log('Rendering broadcast:', {
                  id: selectedBroadcast.id,
                  message_text: selectedBroadcast.message_text,
                  attachment_type: selectedBroadcast.attachment_type,
                  attachment_url: selectedBroadcast.attachment_url,
                  button_text: selectedBroadcast.button_text,
                  button_url: selectedBroadcast.button_url
                });
                return null;
              })()}
              
              {/* Telegram Message Preview */}
              <div style={{
                backgroundColor: '#0e1621',
                padding: '24px',
                borderRadius: '8px',
                marginBottom: '24px'
              }}>
                <div style={{
                  maxWidth: '500px',
                  margin: '0 auto'
                }}>
                  {/* Message Bubble */}
                  <div style={{
                    backgroundColor: '#1c2733',
                    borderRadius: '12px',
                    padding: '0',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
                    overflow: 'hidden'
                  }}>
                    {/* Media Attachment */}
                    {selectedBroadcast.attachment_type && selectedBroadcast.attachment_url && (
                      <div style={{
                        position: 'relative',
                        width: '100%',
                        maxHeight: '400px',
                        overflow: 'hidden',
                        backgroundColor: '#000'
                      }}>
                        {selectedBroadcast.attachment_type === 'image' && (
                          <img 
                            src={selectedBroadcast.attachment_url.startsWith('/uploads') 
                              ? `http://localhost:8001${selectedBroadcast.attachment_url}` 
                              : selectedBroadcast.attachment_url}
                            alt="Preview"
                            style={{
                              width: '100%',
                              height: 'auto',
                              display: 'block'
                            }}
                          />
                        )}
                        {selectedBroadcast.attachment_type === 'video' && (
                          <video 
                            src={selectedBroadcast.attachment_url.startsWith('/uploads') 
                              ? `http://localhost:8001${selectedBroadcast.attachment_url}` 
                              : selectedBroadcast.attachment_url}
                            controls
                            style={{
                              width: '100%',
                              height: 'auto',
                              display: 'block'
                            }}
                          />
                        )}
                        {selectedBroadcast.attachment_type === 'document' && (
                          <div style={{
                            padding: '16px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            backgroundColor: '#1c2733'
                          }}>
                            <div style={{
                              width: '48px',
                              height: '48px',
                              borderRadius: '8px',
                              backgroundColor: '#2b5278',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '24px'
                            }}>
                              📄
                            </div>
                            <div style={{
                              flex: 1,
                              minWidth: 0
                            }}>
                              <div style={{
                                color: '#fff',
                                fontSize: '14px',
                                fontWeight: 500,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}>
                                {selectedBroadcast.attachment_url.split('/').pop()}
                              </div>
                              <div style={{
                                color: '#8a96a5',
                                fontSize: '13px',
                                marginTop: '2px'
                              }}>
                                Документ
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Message Text */}
                    {selectedBroadcast.message_text && (
                      <div style={{
                        padding: selectedBroadcast.attachment_type ? '12px 16px 16px 16px' : '12px 16px',
                        color: '#fff',
                        fontSize: '15px',
                        lineHeight: '1.5',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {selectedBroadcast.message_text}
                      </div>
                    )}

                    {/* Inline Button */}
                    {selectedBroadcast.button_text && selectedBroadcast.button_url && (
                      <div style={{
                        padding: selectedBroadcast.message_text || selectedBroadcast.attachment_type ? '0 12px 12px 12px' : '12px',
                        display: 'flex',
                        gap: '8px'
                      }}>
                        <div style={{
                          flex: 1,
                          backgroundColor: '#2b5278',
                          color: '#64b5f6',
                          padding: '10px 16px',
                          borderRadius: '8px',
                          textAlign: 'center',
                          fontSize: '14px',
                          fontWeight: 500,
                          cursor: 'pointer',
                          transition: 'background-color 0.2s',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '6px'
                        }}>
                          {selectedBroadcast.button_text}
                          <span style={{fontSize: '12px'}}>🔗</span>
                        </div>
                      </div>
                    )}

                    {/* Message Footer */}
                    <div style={{
                      padding: selectedBroadcast.button_text ? '0 16px 8px 16px' : '0 16px 8px 16px',
                      marginTop: selectedBroadcast.button_text ? '0' : selectedBroadcast.message_text || selectedBroadcast.attachment_type ? '-4px' : '0',
                      display: 'flex',
                      justifyContent: 'flex-end',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <span style={{
                        fontSize: '12px',
                        color: '#8a96a5'
                      }}>
                        {new Date(selectedBroadcast.created_at).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span style={{
                        fontSize: '14px',
                        color: '#8a96a5'
                      }}>
                        ✓✓
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Statistics Section */}
              <div className="admin-form">
                <div className="admin-form__group">
                  <label className="admin-form__label">Інформація про розсилку</label>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '12px',
                    fontSize: '14px'
                  }}>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <div style={{color: '#6b7280', fontSize: '12px', marginBottom: '4px'}}>Цільова група</div>
                      <div style={{fontWeight: 500}}>{getTargetGroupName(selectedBroadcast.target_group)}</div>
                    </div>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <div style={{color: '#6b7280', fontSize: '12px', marginBottom: '4px'}}>Статус</div>
                      <div>{getStatusBadge(selectedBroadcast.status)}</div>
                    </div>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <div style={{color: '#6b7280', fontSize: '12px', marginBottom: '4px'}}>Отримувачів</div>
                      <div style={{fontWeight: 500, fontSize: '18px'}}>{selectedBroadcast.total_recipients}</div>
                    </div>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <div style={{color: '#6b7280', fontSize: '12px', marginBottom: '4px'}}>Відправлено</div>
                      <div style={{fontWeight: 500, fontSize: '18px', color: 'var(--color-success)'}}>{selectedBroadcast.sent_count}</div>
                    </div>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <div style={{color: '#6b7280', fontSize: '12px', marginBottom: '4px'}}>Помилок</div>
                      <div style={{fontWeight: 500, fontSize: '18px', color: 'var(--color-danger)'}}>{selectedBroadcast.failed_count}</div>
                    </div>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <div style={{color: '#6b7280', fontSize: '12px', marginBottom: '4px'}}>Створено</div>
                      <div style={{fontWeight: 500, fontSize: '13px'}}>{new Date(selectedBroadcast.created_at).toLocaleString('uk-UA')}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="admin-modal__actions">
              <button
                type="button"
                className="admin-btn admin-btn--secondary"
                onClick={() => setShowDetailModal(false)}
              >
                Закрити
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full Log Modal */}
      {showFullLogModal && (
        <div className="admin-modal" onClick={() => setShowFullLogModal(false)}>
          <div className="admin-modal__backdrop" />
          <div className="admin-modal__content admin-modal__content--lg" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal__header">
              <h2 className="admin-modal__title">Повний лог розсилки</h2>
              <button
                onClick={() => setShowFullLogModal(false)}
                className="admin-modal__close"
                type="button"
                title="Закрити"
              >
                <span>✕</span>
              </button>
            </div>

            <div className="admin-modal__body">
              <div style={{
                backgroundColor: '#1e1e1e',
                color: '#d4d4d4',
                padding: '16px',
                borderRadius: '8px',
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                fontSize: '12px',
                lineHeight: '1.6',
                maxHeight: '500px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {fullLogContent || 'Немає даних про лог'}
              </div>
            </div>

            <div className="admin-modal__actions">
              <button
                type="button"
                className="admin-btn admin-btn--secondary"
                onClick={() => setShowFullLogModal(false)}
              >
                Закрити
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Log Modal */}
      {showErrorModal && (
        <div className="admin-modal" onClick={() => setShowErrorModal(false)}>
          <div className="admin-modal__backdrop" />
          <div className="admin-modal__content admin-modal__content--lg" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal__header">
              <h2 className="admin-modal__title">Лог помилок розсилки</h2>
              <button
                onClick={() => setShowErrorModal(false)}
                className="admin-modal__close"
                type="button"
                title="Закрити"
              >
                <span>✕</span>
              </button>
            </div>

            <div className="admin-modal__body">
              <div style={{
                backgroundColor: '#1e1e1e',
                color: '#d4d4d4',
                padding: '16px',
                borderRadius: '8px',
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                fontSize: '12px',
                lineHeight: '1.6',
                maxHeight: '500px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {errorLogContent || 'Немає даних про помилки'}
              </div>
            </div>

            <div className="admin-modal__actions">
              <button
                type="button"
                className="admin-btn admin-btn--secondary"
                onClick={() => setShowErrorModal(false)}
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
