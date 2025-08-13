'use client';

import './SimpleFooter.scss';

interface SimpleFooterProps {
  className?: string;
}

export default function SimpleFooter({ className = '' }: SimpleFooterProps) {
  const currentYear = new Date().getFullYear();

  return (
    <footer className={`simple-footer ${className}`}>
      <div className="simple-footer-container">
        <p>© {currentYear} DeepCuts. All rights reserved.</p>
      </div>
    </footer>
  );
}