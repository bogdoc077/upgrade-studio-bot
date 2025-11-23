'use client';

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  itemName?: string;
  isDeleting?: boolean;
}

export default function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  itemName,
  isDeleting = false
}: DeleteConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className="admin-modal" onClick={onClose}>
      <div className="admin-modal__backdrop" />
      <div className="admin-modal__content admin-modal__content--sm" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal__body" style={{ textAlign: 'center' }}>
          <div className="admin-modal__icon-wrapper admin-modal__icon-wrapper--danger">
            <ExclamationTriangleIcon className="admin-modal__icon" />
          </div>
          
          <h2 className="admin-modal__title" style={{ marginBottom: 'var(--spacing-sm)' }}>
            {title}
          </h2>
          
          <p className="admin-modal__text">
            {message}
          </p>
          
          {itemName && (
            <p className="admin-modal__highlight">
              {itemName}
            </p>
          )}
        </div>

        <div className="admin-modal__actions">
          <button
            onClick={onClose}
            className="admin-btn admin-btn--secondary"
            type="button"
            disabled={isDeleting}
          >
            Скасувати
          </button>
          <button
            onClick={onConfirm}
            className="admin-btn admin-btn--danger"
            type="button"
            disabled={isDeleting}
          >
            {isDeleting ? 'Видалення...' : 'Видалити'}
          </button>
        </div>
      </div>
    </div>
  );
}
