'use client';

import { useState } from 'react';
import { 
  SpeakerWaveIcon,
  InformationCircleIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';

export default function BroadcastsPage() {
  return (
    <div className="admin-page">
      {/* Header */}
      <div className="admin-page__header">
        <h1 className="admin-page__title">Розсилки</h1>
        <p className="admin-page__subtitle">
          Система масових повідомлень для користувачів бота
        </p>
      </div>

      {/* Coming Soon Card */}
      <div className="admin-card">
        <div className="admin-card__body">
          <div className="text-center py-16">
            <SpeakerWaveIcon className="w-16 h-16 text-gray-400 mx-auto mb-6" />
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Функція в розробці
            </h3>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              Система розсилок наразі перебуває в стадії розробки. 
              Незабаром тут з'явиться можливість створювати та відправляти 
              масові повідомлення користувачам бота.
            </p>
            
            {/* Planned Features */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-4xl mx-auto">
              <div className="text-center p-6 bg-gray-50 rounded-lg">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <SpeakerWaveIcon className="w-6 h-6 text-blue-600" />
                </div>
                <h4 className="font-medium text-gray-900 mb-2">Масові розсилки</h4>
                <p className="text-sm text-gray-600">
                  Відправка повідомлень всім користувачам або вибраним групам
                </p>
              </div>

              <div className="text-center p-6 bg-gray-50 rounded-lg">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <Cog6ToothIcon className="w-6 h-6 text-green-600" />
                </div>
                <h4 className="font-medium text-gray-900 mb-2">Автоматизація</h4>
                <p className="text-sm text-gray-600">
                  Налаштування автоматичних розсилок за розкладом
                </p>
              </div>

              <div className="text-center p-6 bg-gray-50 rounded-lg">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <InformationCircleIcon className="w-6 h-6 text-purple-600" />
                </div>
                <h4 className="font-medium text-gray-900 mb-2">Аналітика</h4>
                <p className="text-sm text-gray-600">
                  Статистика доставки та взаємодії користувачів
                </p>
              </div>
            </div>

            <div className="mt-8 p-4 bg-blue-50 rounded-lg max-w-md mx-auto">
              <p className="text-sm text-blue-800">
                <strong>Очікувана дата запуску:</strong> Q1 2026
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}