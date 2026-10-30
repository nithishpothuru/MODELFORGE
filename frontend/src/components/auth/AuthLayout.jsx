import React from 'react';
import { Link } from 'react-router-dom';
import logoFrame240 from '../../assets/sections/logo_frame240.png';
import { ArrowLeft } from 'lucide-react';

export default function AuthLayout({ children, title, subtitle }) {
  return (
    <div className="mf-auth-container">
      {/* Background ambient lighting */}
      <div className="mf-auth-ambient-glow" />

      {/* Top bar back to landing */}
      <div className="mf-auth-nav">
        <Link to="/" className="mf-auth-back-link">
          <ArrowLeft size={16} />
          <span>Back to ModelForge</span>
        </Link>
      </div>

      <div className="mf-auth-card-wrapper">
        <div className="mf-auth-card">
          {/* Logo & Headline */}
          <div className="mf-auth-header">
            <Link to="/" className="mf-auth-logo-link">
              <img src={logoFrame240} alt="ModelForge Logo" className="mf-auth-logo-img" />
              <span className="mf-auth-brand-name">
                Model<span className="text-[#00D6FF]">Forge</span>
              </span>
            </Link>

            <h1 className="mf-auth-title">{title}</h1>
            {subtitle && <p className="mf-auth-subtitle">{subtitle}</p>}
          </div>

          {/* Form Content */}
          <div className="mf-auth-body">{children}</div>
        </div>

        {/* Footer info */}
        <p className="mf-auth-footer-text">
          Protected by ModelForge Security &bull; Zero-Trust ML Infrastructure
        </p>
      </div>
    </div>
  );
}

