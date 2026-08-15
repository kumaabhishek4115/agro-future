import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Agro Future – Farmer Portal',
  description: 'Farmer Carbon Credit Marketplace',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
