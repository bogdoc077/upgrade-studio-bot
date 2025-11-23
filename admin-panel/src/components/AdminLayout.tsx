'use client';

import { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import MobileHeader from './MobileHeader';

interface AdminLayoutProps {
  children: React.ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const closeSidebar = () => {
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  };

  return (
    <div className="admin-layout">
      {isMobile && <MobileHeader onMenuToggle={toggleSidebar} />}
      
      <Sidebar 
        isOpen={isSidebarOpen} 
        onToggle={!isMobile ? toggleSidebar : undefined}
        onClose={isMobile ? closeSidebar : undefined}
      />
      
      <main className={`admin-layout__main ${!isSidebarOpen || isMobile ? 'admin-layout__main--full' : ''}`}>
        <div className="admin-layout__content">
          {children}
        </div>
      </main>
    </div>
  );
}