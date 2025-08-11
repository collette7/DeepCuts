import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from './contexts/AuthContext';

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
          <main>
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
