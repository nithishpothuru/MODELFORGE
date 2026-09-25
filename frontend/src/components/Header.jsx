import React, { useState, useEffect } from 'react';
import { ArrowRight, Menu, X } from 'lucide-react';
import logoFrame240 from '../assets/sections/logo_frame240.png';

export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 30);
      if (mobileMenuOpen && window.scrollY > 120) {
        setMobileMenuOpen(false);
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };

    const handleResize = () => {
      if (window.innerWidth > 920 && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, [mobileMenuOpen]);

  const navLinks = [
    { name: 'Overview', href: '#chapter-hero' },
    { name: 'Technology', href: '#chapter-unpack' },
    { name: 'Workflow', href: '#chapter-container' },
    { name: 'Use Cases', href: '#chapter-share' },
    { name: 'Pricing', href: '#chapter-cta' },
  ];

  return (
    <header className={`modelforge-header ${scrolled ? 'header-scrolled' : ''}`}>
      <div className="header-container">
        {/* Left: Brand Logo (Static Frame 240 Emblem from MODELFORGE_FRAMES) */}
        <a href="#chapter-hero" className="brand-logo" aria-label="ModelForge Home">
          <img src={logoFrame240} alt="ModelForge" className="brand-frame240-logo-img" />
          <span className="brand-text">
            Model<span className="brand-accent">Forge</span>
          </span>
        </a>

        {/* Center: Desktop Navigation */}
        <nav className="desktop-nav" aria-label="Main Navigation">
          <ul className="nav-list">
            {navLinks.map((link) => (
              <li key={link.name} className="nav-item">
                <a href={link.href} className="nav-link">
                  {link.name}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Right: Rounded "Get Started" CTA Button */}
        <div className="header-actions">
          <a href="#chapter-cta" className="btn-get-started">
            <span>Get Started</span>
            <ArrowRight size={14} className="arrow-icon" />
          </a>

          {/* Mobile Menu Toggle */}
          <button
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="mobile-drawer">
          <ul className="mobile-nav-list">
            {navLinks.map((link) => (
              <li key={link.name}>
                <a
                  href={link.href}
                  className="mobile-nav-link"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.name}
                </a>
              </li>
            ))}
            <li className="mobile-cta-item">
              <a
                href="#chapter-cta"
                className="btn-get-started mobile-full"
                onClick={() => setMobileMenuOpen(false)}
              >
                <span>Get Started</span>
                <ArrowRight size={14} />
              </a>
            </li>
          </ul>
        </div>
      )}
    </header>
  );
}
