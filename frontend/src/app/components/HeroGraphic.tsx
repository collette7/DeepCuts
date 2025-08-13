'use client';

import React from 'react';
import './HeroGraphic.scss';

export default function HeroGraphic() {
  return (
    <div className="hero-graphic">
      <div className="hero-graphic-container">
        {/* Flying Birds */}
        <div className="birds-container">
          <div className="bird bird-1">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
          <div className="bird bird-2">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
          <div className="bird bird-3">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
          <div className="bird bird-4">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
          <div className="bird bird-5">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
        </div>

        {/* Central Content */}
        <div className="hero-content">
          {/* DeepCuts Text */}
          <h1 className="hero-title">
            <span className="title-deep">DEEP</span>
            <span className="title-cuts">CUTS</span>
          </h1>
          
          {/* Vinyl Record Globe */}
          <div className="vinyl-globe">
            <div className="vinyl-record">
              <div className="vinyl-outer-ring"></div>
              <div className="vinyl-grooves"></div>
              <div className="vinyl-label">
                <div className="label-text">DEEP</div>
                <div className="label-text-small">CUTS</div>
                <div className="center-hole"></div>
              </div>
              <div className="vinyl-shine"></div>
            </div>
            
            {/* Globe effect with world map silhouette */}
            <div className="globe-overlay">
              <svg className="world-map" viewBox="0 0 200 200" fill="none">
                {/* Simplified world continents */}
                <path d="M20 80C30 70, 50 75, 60 80C70 85, 80 80, 90 85C95 90, 85 95, 80 100C75 105, 65 100, 55 105C45 110, 35 105, 25 100C15 95, 15 85, 20 80Z" fill="rgba(0,0,0,0.3)"/>
                <path d="M110 60C120 55, 140 60, 150 65C160 70, 170 65, 180 70C185 75, 175 80, 170 85C165 90, 155 85, 145 90C135 95, 125 90, 115 85C105 80, 105 70, 110 60Z" fill="rgba(0,0,0,0.3)"/>
                <path d="M30 120C40 115, 60 120, 70 125C80 130, 90 125, 100 130C105 135, 95 140, 90 145C85 150, 75 145, 65 150C55 155, 45 150, 35 145C25 140, 25 130, 30 120Z" fill="rgba(0,0,0,0.3)"/>
              </svg>
            </div>
            
            {/* Spinning animation indicator */}
            <div className="rotation-indicator">
              <div className="indicator-dot"></div>
            </div>
          </div>
          
          {/* Subtitle */}
          <p className="hero-subtitle">Discover the deep cuts that define great music</p>
        </div>

        {/* Additional decorative birds */}
        <div className="background-birds">
          <div className="bg-bird bg-bird-1">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
          <div className="bg-bird bg-bird-2">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
          <div className="bg-bird bg-bird-3">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 12C2 12 5 8 12 8C19 8 22 12 22 12C22 12 19 16 12 16C5 16 2 12 2 12Z M12 10A2 2 0 1 0 12 14A2 2 0 0 0 12 10Z"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}