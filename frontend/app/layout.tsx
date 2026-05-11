import type { Metadata } from 'next';
import RootLayoutWrapper from '@/components/RootLayoutWrapper';
import './globals.css';

export const metadata: Metadata = {
  title: 'Transfreezer Insight Suite',
  description: 'Plataforma web modular para analítica y pronóstico operativo.'
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <RootLayoutWrapper>{children}</RootLayoutWrapper>
      </body>
    </html>
  );
}
