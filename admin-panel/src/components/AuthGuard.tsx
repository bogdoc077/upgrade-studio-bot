'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    checkAuth();
  }, [pathname]);

  const checkAuth = () => {
    try {
      // Перевіряємо токен в localStorage
      const token = localStorage.getItem('auth_token');
      
      // Перевіряємо токен в cookies
      const cookieToken = document.cookie
        .split(';')
        .find(row => row.trim().startsWith('auth_token='))
        ?.split('=')[1];

      const hasValidToken = token || cookieToken;

      if (!hasValidToken) {
        // Перенаправляємо на логін з поточною сторінкою
        const loginUrl = `/login?redirect=${encodeURIComponent(pathname)}`;
        router.push(loginUrl);
        setIsAuthenticated(false);
        return;
      }

      setIsAuthenticated(true);
    } catch (error) {
      console.error('Auth check error:', error);
      setIsAuthenticated(false);
      router.push('/login');
    }
  };

  // Показуємо завантаження поки перевіряємо авторизацію
  if (isAuthenticated === null) {
    return (
      <div className="auth-loading">
        <div className="auth-loading__content">
          <div className="auth-loading__spinner"></div>
          <p className="auth-loading__text">Перевірка авторизації...</p>
        </div>
      </div>
    );
  }

  // Якщо не авторизований - не показуємо контент
  if (!isAuthenticated) {
    return null;
  }

  // Якщо авторизований - показуємо контент
  return <>{children}</>;
}