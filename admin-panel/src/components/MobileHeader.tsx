'use client';

import Image from 'next/image';
import { Bars3Icon } from '@heroicons/react/24/outline';

interface MobileHeaderProps {
  onMenuToggle: () => void;
}

export default function MobileHeader({ onMenuToggle }: MobileHeaderProps) {
  return (
    <header className="admin-mobile-header">
      <div className="admin-mobile-header__logo">
        <Image 
          src="/logo.svg" 
          alt="Upgrade21 Studio Logo" 
          width={40} 
          height={40}
          priority
        />
      </div>
      
      <button 
        className="admin-mobile-header__menu-btn"
        onClick={onMenuToggle}
        aria-label="Відкрити меню"
      >
        <Bars3Icon className="w-6 h-6" />
      </button>
    </header>
  );
}
