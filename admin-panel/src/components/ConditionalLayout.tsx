'use client';

import { usePathname } from 'next/navigation';
import AdminLayout from './AdminLayout';
import AuthGuard from './AuthGuard';

interface ConditionalLayoutProps {
  children: React.ReactNode;
}

export default function ConditionalLayout({ children }: ConditionalLayoutProps) {
  const pathname = usePathname();
  
  // Сторінки, які не потребують авторизації
  const publicPages = ['/login'];
  const isPublicPage = publicPages.includes(pathname);
  
  // Для публічних сторінок не використовуємо AuthGuard і AdminLayout
  if (isPublicPage) {
    return <>{children}</>;
  }
  
  // Для приватних сторінок використовуємо AuthGuard і AdminLayout
  return (
    <AuthGuard>
      <AdminLayout>
        {children}
      </AdminLayout>
    </AuthGuard>
  );
}