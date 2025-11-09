'use client'

import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { User, apiClient, handleApiError } from '@/utils/api'

interface UserEditModalProps {
  user: User | null
  isOpen: boolean
  onClose: () => void
  onUserUpdated: () => void
}

export default function UserEditModal({ user, isOpen, onClose, onUserUpdated }: UserEditModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubscriptionAction = async (action: 'activate' | 'deactivate' | 'extend') => {
    if (!user) return

    try {
      setLoading(true)
      setError(null)
      
      await apiClient.updateUserSubscription(user.id, action)
      onUserUpdated()
      onClose()
    } catch (err) {
      setError(handleApiError(err))
    } finally {
      setLoading(false)
    }
  }

  if (!user) return null

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="modal" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="modal__backdrop" />
        </Transition.Child>

        <div className="modal__container">
          <div className="modal__content-wrapper">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="modal__panel">
                {/* Header */}
                <div className="modal__header">
                  <div className="modal__title-section">
                    <Dialog.Title className="modal__title">
                      Edit User: {user.first_name} {user.last_name}
                    </Dialog.Title>
                    <p className="modal__subtitle">
                      Manage subscription and user settings
                    </p>
                  </div>
                  <button
                    type="button"
                    className="modal__close-btn"
                    onClick={onClose}
                  >
                    <XMarkIcon className="modal__close-icon" />
                  </button>
                </div>

                {/* Content */}
                <div className="modal__body">
                  {error && (
                    <div className="alert alert--error">
                      <div className="alert__content">{error}</div>
                    </div>
                  )}

                  {/* User Info */}
                  <div className="user-edit__section">
                    <h4 className="user-edit__section-title">User Information</h4>
                    <div className="user-edit__info-grid">
                      <div className="user-edit__info-item">
                        <span className="user-edit__info-label">Telegram ID:</span>
                        <span className="user-edit__info-value">{user.telegram_id}</span>
                      </div>
                      <div className="user-edit__info-item">
                        <span className="user-edit__info-label">Username:</span>
                        <span className="user-edit__info-value">@{user.username || 'No username'}</span>
                      </div>
                      <div className="user-edit__info-item">
                        <span className="user-edit__info-label">Role:</span>
                        <span className="user-edit__info-value">{user.role}</span>
                      </div>
                      <div className="user-edit__info-item">
                        <span className="user-edit__info-label">Status:</span>
                        <span className={`status ${user.subscription_active ? 'status--success' : 'status--error'}`}>
                          {user.subscription_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Subscription Management */}
                  <div className="user-edit__section">
                    <h4 className="user-edit__section-title">Subscription Management</h4>
                    <div className="user-edit__actions">
                      {!user.subscription_active ? (
                        <button
                          onClick={() => handleSubscriptionAction('activate')}
                          disabled={loading}
                          className="btn btn--success"
                        >
                          {loading ? 'Activating...' : 'Activate Subscription'}
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => handleSubscriptionAction('extend')}
                            disabled={loading}
                            className="btn btn--primary"
                          >
                            {loading ? 'Extending...' : 'Extend by 30 days'}
                          </button>
                          <button
                            onClick={() => handleSubscriptionAction('deactivate')}
                            disabled={loading}
                            className="btn btn--warning"
                          >
                            {loading ? 'Deactivating...' : 'Deactivate Subscription'}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="modal__footer">
                  <button
                    type="button"
                    className="btn btn--secondary"
                    onClick={onClose}
                  >
                    Close
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}