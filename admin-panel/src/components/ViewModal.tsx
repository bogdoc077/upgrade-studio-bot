'use client';

import { XMarkIcon } from '@heroicons/react/24/outline';

interface ViewField {
  label: string;
  value: string | number | boolean | null | undefined;
  type?: 'text' | 'status' | 'date' | 'currency' | 'boolean';
}

interface ViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  fields: ViewField[];
}

export default function ViewModal({ isOpen, onClose, title, fields }: ViewModalProps) {
  if (!isOpen) return null;

  const formatValue = (field: ViewField) => {
    const { value, type } = field;

    if (value === null || value === undefined) return '—';

    switch (type) {
      case 'date':
        return new Date(value as string).toLocaleDateString('uk-UA', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      
      case 'currency':
        return `€${Number(value).toFixed(2)}`;
      
      case 'boolean':
        return value ? 'Так' : 'Ні';
      
      case 'status':
        return (
          <span className={`admin-status ${
            value === 'active' || value === 'succeeded' || value === 'completed'
              ? 'admin-status--success'
              : value === 'pending' || value === 'processing'
              ? 'admin-status--pending'
              : 'admin-status--neutral'
          }`}>
            {String(value)}
          </span>
        );
      
      default:
        return String(value);
    }
  };

  return (
    <div className="admin-modal" onClick={onClose}>
      <div className="admin-modal__backdrop" />
      <div className="admin-modal__content" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal__header">
          <h2 className="admin-modal__title">{title}</h2>
          <button
            onClick={onClose}
            className="admin-modal__close"
            type="button"
            title="Закрити"
          >
            <XMarkIcon />
          </button>
        </div>

        <div className="admin-modal__body">
          <div className="admin-view-grid">
            {fields.map((field, index) => (
              <div key={index} className="admin-view-item">
                <div className="admin-view-item__label">{field.label}</div>
                <div className="admin-view-item__value">{formatValue(field)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="admin-modal__actions">
          <button
            onClick={onClose}
            className="admin-btn admin-btn--secondary"
            type="button"
          >
            Закрити
          </button>
        </div>
      </div>
    </div>
  );
}
