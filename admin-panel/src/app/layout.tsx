import type { Metadata } from 'next';
import ConditionalLayout from '@/components/ConditionalLayout';
import './globals.css';
import './components.css';

export const metadata: Metadata = {
  title: 'Upgrade Studio Admin',
  description: 'Admin panel for Upgrade Studio Bot',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="uk">
      <body>
        <ConditionalLayout>
          {children}
        </ConditionalLayout>
      </body>
    </html>
  );
}