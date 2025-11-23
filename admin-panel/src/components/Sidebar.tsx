'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { 
  HomeIcon,
  UsersIcon,
  CreditCardIcon,
  SpeakerWaveIcon,
  UserGroupIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon
} from '@heroicons/react/24/outline';
import { MenuItem } from '@/types';

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: () => void;
  onClose?: () => void;
}

const menuItems: MenuItem[] = [
  { id: 'dashboard', label: 'Дашборд', path: '/', icon: 'HomeIcon' },
  { id: 'users', label: 'Користувачі', path: '/users', icon: 'UsersIcon' },
  { id: 'payments', label: 'Платежі', path: '/payments', icon: 'CreditCardIcon' },
  { id: 'broadcasts', label: 'Розсилки', path: '/broadcasts', icon: 'SpeakerWaveIcon' },
  { id: 'admins', label: 'Адміни', path: '/admins', icon: 'UserGroupIcon' },
  { id: 'settings', label: 'Налаштування', path: '/settings', icon: 'Cog6ToothIcon' },
];

const iconComponents = {
  HomeIcon,
  UsersIcon,
  CreditCardIcon,
  SpeakerWaveIcon,
  UserGroupIcon,
  Cog6ToothIcon,
};

export default function Sidebar({ isOpen = true, onToggle, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  // Отримуємо дані поточного адміна
  const getAdminData = () => {
    if (typeof localStorage !== 'undefined') {
      const adminData = localStorage.getItem('admin_data');
      if (adminData) {
        try {
          return JSON.parse(adminData);
        } catch (error) {
          console.error('Error parsing admin data:', error);
        }
      }
    }
    return null;
  };

  const adminData = getAdminData();

  const handleLogout = () => {
    const confirmLogout = window.confirm('Ви впевнені, що хочете вийти з системи?');
    
    if (!confirmLogout) {
      return;
    }
    
    try {
      // Видаляємо токен з localStorage
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('admin_data');
      }
      
      // Видаляємо cookie з токеном
      document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
      
      // Закриваємо сайдбар на мобільному
      if (onClose) {
        onClose();
      }
      
      // Перенаправляємо на сторінку логіну
      router.push('/login');
      
    } catch (error) {
      console.error('Logout error:', error);
      // Все одно перенаправляємо на логін навіть при помилці
      router.push('/login');
    }
  };

  return (
    <>
      {/* Mobile toggle button */}
      {onToggle && (
        <button 
          className="admin-layout__toggle"
          onClick={onToggle}
          aria-label="Відкрити меню"
        >
          <Bars3Icon className="w-6 h-6" />
        </button>
      )}

      {/* Mobile overlay */}
      {isOpen && onClose && (
        <div 
          className="admin-layout__overlay admin-layout__overlay--visible"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside className={`admin-layout__sidebar ${isOpen ? 'admin-layout__sidebar--visible' : 'admin-layout__sidebar--hidden'}`}>
        <div className="admin-sidebar">
          {/* Header */}
          <div className="admin-sidebar__header">
            <Link href="/" className="admin-sidebar__logo">
              <div className="admin-sidebar__logo-icon">
                <Image 
                  src="/logo.svg" 
                  alt="Upgrade21 Studio Logo" 
                  width={32} 
                  height={32}
                  priority
                />
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="admin-sidebar__nav">
            <ul className="admin-sidebar__menu">
              {menuItems.map((item) => {
                const IconComponent = iconComponents[item.icon as keyof typeof iconComponents];
                const isActive = pathname === item.path || (item.path !== '/' && pathname.startsWith(item.path));
                
                return (
                  <li key={item.id} className="admin-sidebar__menu-item">
                    <Link 
                      href={item.path}
                      className={`admin-sidebar__menu-link ${isActive ? 'admin-sidebar__menu-link--active' : ''}`}
                      onClick={onClose}
                    >
                      <IconComponent className="admin-sidebar__menu-icon" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Footer */}
          <div className="admin-sidebar__footer">
            {/* Admin info */}
            {adminData && (
              <div className="admin-sidebar__user">
                <div className="admin-sidebar__user-avatar">
                  {adminData.first_name?.[0]?.toUpperCase() || 'A'}
                </div>
                <div className="admin-sidebar__user-info">
                  <div className="admin-sidebar__user-name">
                    {adminData.first_name} {adminData.last_name || ''}
                  </div>
                  <div className="admin-sidebar__user-role">
                    {adminData.role || 'Адмін'}
                  </div>
                </div>
              </div>
            )}
            
            <button 
              className="admin-sidebar__logout"
              onClick={handleLogout}
            >
              <ArrowRightOnRectangleIcon className="admin-sidebar__menu-icon" />
              <span>Вийти</span>
            </button>
            <div className="admin-sidebar__version">
              Версія 1.0.0
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}