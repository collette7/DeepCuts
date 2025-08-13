import type { Metadata } from "next";
import "./globals.scss";
import { AuthProvider } from './contexts/AuthContext';
import AuthErrorHandler from '@/components/AuthErrorHandler';
import SimpleFooter from './components/SimpleFooter';

export const metadata: Metadata = {
  title: "DeepCuts Music Discovery",
  description: "Recommendations that understand your taste — not just your plays.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning={true}>
        <AuthProvider>
          <AuthErrorHandler />
          <main>
            {children}
          </main>
          <SimpleFooter />
        </AuthProvider>
      </body>
    </html>
  );
}
