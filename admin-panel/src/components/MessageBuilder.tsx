'use client';

import { useState } from 'react';
import { 
  PhotoIcon, 
  VideoCameraIcon, 
  DocumentIcon, 
  ChatBubbleLeftIcon,
  LinkIcon,
  PlusIcon,
  TrashIcon,
  ArrowUpIcon,
  ArrowDownIcon
} from '@heroicons/react/24/outline';

export interface MessageBlock {
  id: string;
  type: 'text' | 'image' | 'video' | 'document' | 'button';
  content: string;
  file?: File;
  fileUrl?: string;
  buttonText?: string;
  buttonUrl?: string;
}

interface MessageBuilderProps {
  blocks: MessageBlock[];
  onChange: (blocks: MessageBlock[]) => void;
  onFileUpload: (file: File) => Promise<{ url: string; type: string }>;
}

export default function MessageBuilder({ blocks, onChange, onFileUpload }: MessageBuilderProps) {
  const [uploading, setUploading] = useState<string | null>(null);
  const [showAddMenu, setShowAddMenu] = useState(false);

  const addBlock = (type: MessageBlock['type']) => {
    const newBlock: MessageBlock = {
      id: `block-${Date.now()}`,
      type,
      content: '',
    };
    onChange([...blocks, newBlock]);
    setShowAddMenu(false);
  };

  const updateBlock = (id: string, updates: Partial<MessageBlock>) => {
    onChange(blocks.map(block => 
      block.id === id ? { ...block, ...updates } : block
    ));
  };

  const removeBlock = (id: string) => {
    onChange(blocks.filter(block => block.id !== id));
  };

  const moveBlock = (id: string, direction: 'up' | 'down') => {
    const index = blocks.findIndex(block => block.id === id);
    if (
      (direction === 'up' && index === 0) || 
      (direction === 'down' && index === blocks.length - 1)
    ) return;

    const newBlocks = [...blocks];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    [newBlocks[index], newBlocks[targetIndex]] = [newBlocks[targetIndex], newBlocks[index]];
    onChange(newBlocks);
  };

  const handleFileSelect = async (blockId: string, file: File) => {
    setUploading(blockId);
    try {
      const result = await onFileUpload(file);
      updateBlock(blockId, { 
        file, 
        fileUrl: result.url,
        content: file.name 
      });
    } catch (error) {
      console.error('Upload error:', error);
      alert('Помилка завантаження файлу');
    } finally {
      setUploading(null);
    }
  };

  const getBlockIcon = (type: MessageBlock['type']) => {
    switch (type) {
      case 'text': return <ChatBubbleLeftIcon className="w-5 h-5" />;
      case 'image': return <PhotoIcon className="w-5 h-5" />;
      case 'video': return <VideoCameraIcon className="w-5 h-5" />;
      case 'document': return <DocumentIcon className="w-5 h-5" />;
      case 'button': return <LinkIcon className="w-5 h-5" />;
    }
  };

  const getBlockLabel = (type: MessageBlock['type']) => {
    switch (type) {
      case 'text': return 'Текст';
      case 'image': return 'Зображення';
      case 'video': return 'Відео';
      case 'document': return 'Документ';
      case 'button': return 'Кнопка';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Blocks List */}
      {blocks.map((block, index) => (
        <div
          key={block.id}
          style={{
            border: '2px solid #e5e7eb',
            borderRadius: '8px',
            padding: '16px',
            backgroundColor: '#fff'
          }}
        >
          {/* Block Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6b7280' }}>
              {getBlockIcon(block.type)}
              <span style={{ fontWeight: 500, fontSize: '14px' }}>{getBlockLabel(block.type)}</span>
            </div>
            <div style={{ display: 'flex', gap: '4px' }}>
              {index > 0 && (
                <button
                  type="button"
                  onClick={() => moveBlock(block.id, 'up')}
                  style={{
                    padding: '6px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    backgroundColor: '#fff',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                  title="Вгору"
                >
                  <ArrowUpIcon className="w-4 h-4" style={{ color: '#6b7280' }} />
                </button>
              )}
              {index < blocks.length - 1 && (
                <button
                  type="button"
                  onClick={() => moveBlock(block.id, 'down')}
                  style={{
                    padding: '6px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    backgroundColor: '#fff',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                  title="Вниз"
                >
                  <ArrowDownIcon className="w-4 h-4" style={{ color: '#6b7280' }} />
                </button>
              )}
              <button
                type="button"
                onClick={() => removeBlock(block.id)}
                style={{
                  padding: '6px',
                  border: '1px solid #fca5a5',
                  borderRadius: '4px',
                  backgroundColor: '#fff',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="Видалити"
              >
                <TrashIcon className="w-4 h-4" style={{ color: '#ef4444' }} />
              </button>
            </div>
          </div>

          {/* Block Content */}
          {block.type === 'text' && (
            <textarea
              value={block.content}
              onChange={(e) => updateBlock(block.id, { content: e.target.value })}
              placeholder="Введіть текст повідомлення..."
              style={{
                width: '100%',
                minHeight: '100px',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px',
                fontFamily: 'inherit',
                resize: 'vertical'
              }}
            />
          )}

          {(block.type === 'image' || block.type === 'video' || block.type === 'document') && (
            <div>
              {!block.fileUrl ? (
                <div>
                  <input
                    type="file"
                    id={`file-${block.id}`}
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileSelect(block.id, file);
                    }}
                    accept={
                      block.type === 'image' ? 'image/*' :
                      block.type === 'video' ? 'video/*' :
                      '.pdf,.zip,.doc,.docx,.xls,.xlsx'
                    }
                    disabled={uploading === block.id}
                  />
                  <label
                    htmlFor={`file-${block.id}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      padding: '24px',
                      border: '2px dashed #d1d5db',
                      borderRadius: '6px',
                      cursor: uploading === block.id ? 'not-allowed' : 'pointer',
                      backgroundColor: '#f9fafb',
                      transition: 'all 0.2s'
                    }}
                  >
                    {uploading === block.id ? (
                      <span style={{ color: '#6b7280' }}>Завантаження...</span>
                    ) : (
                      <>
                        <PlusIcon className="w-5 h-5" style={{ color: '#6b7280' }} />
                        <span style={{ color: '#6b7280', fontSize: '14px' }}>
                          Виберіть {block.type === 'image' ? 'зображення' : block.type === 'video' ? 'відео' : 'файл'}
                        </span>
                      </>
                    )}
                  </label>
                </div>
              ) : (
                <div style={{
                  position: 'relative',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  overflow: 'hidden'
                }}>
                  {block.type === 'image' && block.fileUrl && (
                    <img
                      src={`http://localhost:8001${block.fileUrl}`}
                      alt="Preview"
                      style={{ width: '100%', height: 'auto', display: 'block' }}
                    />
                  )}
                  {block.type === 'video' && block.fileUrl && (
                    <video
                      src={`http://localhost:8001${block.fileUrl}`}
                      controls
                      style={{ width: '100%', height: 'auto', display: 'block' }}
                    />
                  )}
                  {block.type === 'document' && (
                    <div style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <DocumentIcon className="w-8 h-8" style={{ color: '#6b7280' }} />
                      <span style={{ fontSize: '14px', color: '#374151' }}>{block.content}</span>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => updateBlock(block.id, { fileUrl: '', file: undefined, content: '' })}
                    style={{
                      position: 'absolute',
                      top: '8px',
                      right: '8px',
                      padding: '6px',
                      backgroundColor: 'rgba(239, 68, 68, 0.9)',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                    title="Видалити файл"
                  >
                    <TrashIcon className="w-4 h-4" style={{ color: '#fff' }} />
                  </button>
                </div>
              )}
            </div>
          )}

          {block.type === 'button' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input
                type="text"
                value={block.buttonText || ''}
                onChange={(e) => updateBlock(block.id, { buttonText: e.target.value })}
                placeholder="Текст кнопки"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              />
              <input
                type="url"
                value={block.buttonUrl || ''}
                onChange={(e) => updateBlock(block.id, { buttonUrl: e.target.value })}
                placeholder="https://example.com"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              />
            </div>
          )}
        </div>
      ))}

      {/* Add Block Button */}
      <div style={{ position: 'relative' }}>
        <button
          type="button"
          onClick={() => setShowAddMenu(!showAddMenu)}
          style={{
            width: '100%',
            padding: '16px',
            border: '2px dashed #9ca3af',
            borderRadius: '8px',
            backgroundColor: '#f9fafb',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            color: '#6b7280',
            fontSize: '14px',
            fontWeight: 500,
            transition: 'all 0.2s'
          }}
        >
          <PlusIcon className="w-5 h-5" />
          Додати елемент
        </button>

        {showAddMenu && (
          <>
            {/* Backdrop */}
            <div 
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
                zIndex: 9998
              }}
              onClick={() => setShowAddMenu(false)}
            />
            
            {/* Menu */}
            <div style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
              zIndex: 9999,
              minWidth: '240px',
              maxHeight: '80vh',
              overflow: 'auto'
            }}>
              <div style={{ padding: '8px 0' }}>
                {[
                  { type: 'text' as const, label: 'Текст', icon: ChatBubbleLeftIcon },
                  { type: 'image' as const, label: 'Зображення', icon: PhotoIcon },
                  { type: 'video' as const, label: 'Відео', icon: VideoCameraIcon },
                  { type: 'document' as const, label: 'Документ', icon: DocumentIcon },
                  { type: 'button' as const, label: 'Кнопка', icon: LinkIcon },
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.type}
                      type="button"
                      onClick={() => addBlock(item.type)}
                      style={{
                        width: '100%',
                        padding: '12px 16px',
                        border: 'none',
                        backgroundColor: 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        fontSize: '14px',
                        color: '#374151',
                        transition: 'background-color 0.2s'
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.backgroundColor = '#f3f4f6';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <Icon className="w-5 h-5" style={{ color: '#6b7280' }} />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
