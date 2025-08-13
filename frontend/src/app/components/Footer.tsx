'use client';

import { Heart, Github, Twitter, Mail } from 'lucide-react';
import './Footer.scss';

interface FooterProps {
  className?: string;
}

export default function Footer({ className = '' }: FooterProps) {
  const currentYear = new Date().getFullYear();

  const handleLinkClick = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <footer className={`main-footer ${className}`} role="contentinfo">
      <div className="footer-container">
        {/* Main Footer Content */}
        <div className="footer-content">
          {/* Brand Section */}
          <div className="footer-brand">
            <div className="footer-brand-info">
              <h3 className="footer-brand-name">DeepCuts</h3>
              <p className="footer-brand-tagline">
                Recommendations that understand your taste — not just your plays.
              </p>
            </div>
          </div>

          {/* Links Section */}
          <div className="footer-links">
            <div className="footer-column">
              <h4 className="footer-column-title">Product</h4>
              <ul className="footer-link-list">
                <li>
                  <button 
                    className="footer-link"
                    onClick={() => handleLinkClick('/about')}
                    aria-label="Learn more about DeepCuts"
                  >
                    About
                  </button>
                </li>
                <li>
                  <button 
                    className="footer-link"
                    onClick={() => handleLinkClick('/features')}
                    aria-label="Explore DeepCuts features"
                  >
                    Features
                  </button>
                </li>
                <li>
                  <button 
                    className="footer-link"
                    onClick={() => handleLinkClick('/favorites')}
                    aria-label="View your favorites"
                  >
                    My Favorites
                  </button>
                </li>
              </ul>
            </div>

            <div className="footer-column">
              <h4 className="footer-column-title">Legal</h4>
              <ul className="footer-link-list">
                <li>
                  <button 
                    className="footer-link"
                    onClick={() => handleLinkClick('/privacy')}
                    aria-label="Read our privacy policy"
                  >
                    Privacy Policy
                  </button>
                </li>
                <li>
                  <button 
                    className="footer-link"
                    onClick={() => handleLinkClick('/terms')}
                    aria-label="Read our terms of service"
                  >
                    Terms of Service
                  </button>
                </li>
                <li>
                  <button 
                    className="footer-link"
                    onClick={() => handleLinkClick('/contact')}
                    aria-label="Contact us"
                  >
                    Contact
                  </button>
                </li>
              </ul>
            </div>

            <div className="footer-column">
              <h4 className="footer-column-title">Connect</h4>
              <div className="footer-social">
                <button
                  className="footer-social-link"
                  onClick={() => handleLinkClick('https://github.com/deepcuts')}
                  aria-label="Follow us on GitHub"
                  title="GitHub"
                >
                  <Github size={20} />
                </button>
                <button
                  className="footer-social-link"
                  onClick={() => handleLinkClick('https://twitter.com/deepcuts')}
                  aria-label="Follow us on Twitter"
                  title="Twitter"
                >
                  <Twitter size={20} />
                </button>
                <button
                  className="footer-social-link"
                  onClick={() => handleLinkClick('mailto:hello@deepcuts.app')}
                  aria-label="Send us an email"
                  title="Email"
                >
                  <Mail size={20} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="footer-bottom">
          <div className="footer-bottom-content">
            <p className="footer-copyright">
              © {currentYear} DeepCuts. All rights reserved.
            </p>
            <div className="footer-bottom-right">
              <span className="footer-made-with">
                Made with <Heart size={14} className="footer-heart" /> for music lovers
              </span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}