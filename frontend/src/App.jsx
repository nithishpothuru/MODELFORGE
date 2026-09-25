import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Centered3DStage from './components/Centered3DStage';
import CinematicProgressNav from './components/CinematicProgressNav';
 import DockedCodePreview from './components/DockedCodePreview';
import {
  ArrowRight,
  Copy,
  Check,
  Link2,
} from 'lucide-react';
import logoFrame240 from './assets/sections/logo_frame240.png';
import './App.css';

export default function App() {
  const [activeChapter, setActiveChapter] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [toastMessage, setToastMessage] = useState('');
  const [cursorPos, setCursorPos] = useState({ x: -100, y: -100 });
  const [heroContentRevealed, setHeroContentRevealed] = useState(false);

  // Section 03 interactive URL copy state
  const [copiedUrl, setCopiedUrl] = useState(false);
  const shareUrl = 'https://modelforge.app/your-model';

  // Mouse spotlight glow
  useEffect(() => {
    const handleMouseMove = (e) => {
      setCursorPos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Safety timer ensuring hero content reveals gracefully even on slow mobile networks
  useEffect(() => {
    const timer = setTimeout(() => {
      setHeroContentRevealed(true);
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  // Global Scroll Listener calculating progress across the full scrollytelling journey
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(1, Math.max(0, scrollY / docHeight)) : 0;
      setScrollProgress(progress);

      // If user scrolls at all, make sure hero content is revealed
      if (scrollY > 10) {
        setHeroContentRevealed(true);
      }

      // Determine active chapter based on scroll position of sections with responsive threshold
      const sections = ['chapter-hero', 'chapter-unpack', 'chapter-container', 'chapter-share', 'chapter-impact', 'chapter-cta'];
      let currentIdx = 0;
      const threshold = window.innerWidth <= 860 ? window.innerHeight * 0.65 : window.innerHeight * 0.55;
      for (let i = 0; i < sections.length; i++) {
        const el = document.getElementById(sections[i]);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= threshold) {
            currentIdx = i;
          }
        }
      }
      setActiveChapter(currentIdx);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage('');
    }, 3000);
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopiedUrl(true);
      showToast('Model endpoint copied to clipboard!');
      setTimeout(() => setCopiedUrl(false), 2500);
    });
  };

  const handleHeroIntroComplete = () => {
    setHeroContentRevealed(true);
  };

  // Dynamic Background Theme based on active chapter (Harmonized to pure #000000 base)
  const getPageBgStyle = () => {
    switch (activeChapter) {
      case 1:
        return 'theme-bg-unpack'; // Golden amber cast
      case 2:
        return 'theme-bg-container'; // Deep cybernetic blue
      case 3:
        return 'theme-bg-share'; // Network indigo
      case 4:
        return 'theme-bg-impact'; // Cosmic deep navy
      default:
        return 'theme-bg-hero'; // Deep black #000000
    }
  };

  return (
    <div className={`modelforge-scrolly-page ${getPageBgStyle()}`}>
      {/* Header with Frame 240 Logo */}
      <Header />

      {/* Sticky 3D Stage (Strictly Side-by-Side in all chapters — Never under text) */}
      <Centered3DStage
        scrollProgress={scrollProgress}
        activeChapter={activeChapter}
        onHeroIntroComplete={handleHeroIntroComplete}
      />

      {/* Anime.js Style Bottom-Right Stacked Inspector & Cinematic Progress Nav */}
      <DockedCodePreview activeChapter={activeChapter} scrollProgress={scrollProgress} />
      <CinematicProgressNav activeChapter={activeChapter} scrollProgress={scrollProgress} />

      {/* Editorial Content Chapters Scrolling Smoothly Beside the 3D Stage */}
      <div className="scrolly-content-stream">
        {/* ==================================================================
            CHAPTER 00: HERO (Frames 001–048 Right | Minimal Content Left)
            ================================================================== */}
        <section id="chapter-hero" className={`scrolly-chapter-hero ${activeChapter === 0 ? 'chapter-active' : ''}`}>
          <div
            className={`hero-editorial-split-left ${
              heroContentRevealed ? 'hero-content-revealed' : ''
            }`}
          >
            <div className="hero-micro-tag">
              ZIP <span className="arrow">→</span> CONTAINER <span className="arrow">→</span> SHARE
            </div>

            <h1 className="hero-headline">
              <span className="brand-title">
                Model<span className="brand-cyan">Forge</span>
              </span>
              <span className="hero-subheadline">
                Build. Deploy. Share.
              </span>
            </h1>

            <p className="hero-subcopy">
              Turn your machine learning projects into production-ready Docker containers with zero infrastructure setup.
            </p>

            <div className="hero-actions">
              <a href="#chapter-cta" className="btn-hero-primary">
                <span>Get Started</span>
                <ArrowRight size={15} />
              </a>
            </div>
          </div>
        </section>

        {/* ==================================================================
            CHAPTER 01: YOUR PROJECT, UNPACKED (Slow-Motion Disassembly)
            ================================================================== */}
        <section id="chapter-unpack" className={`scrolly-chapter scrolly-chapter-left ${activeChapter === 1 ? 'chapter-active' : ''}`}>
          <div className="scrolly-card-panel">
            <div className="section-badge-row">
              <span className="section-index-num">01</span>
              <span className="section-dash-line" />
              <span className="section-micro-tag">UNPACK & EXTRACT</span>
            </div>

            <h2 className="editorial-heading">
              Your Project, <br />
              <span className="text-white-bright">Unpacked.</span>
            </h2>

            <p className="editorial-subcopy">
              Upload your ML code. ModelForge automatically inspects dependencies, detects PyTorch and CUDA versions, and generates runtime manifests.
            </p>

            <div className="editorial-bullets-list">
              <div className="bullet-clean-item">
                <span className="bullet-bullet-cyan">•</span>
                <span>Deep AST inspection of Python codebase and libraries</span>
              </div>
              <div className="bullet-clean-item">
                <span className="bullet-bullet-cyan">•</span>
                <span>Automatic resolution of PyTorch, CUDA and C++ dependencies</span>
              </div>
            </div>
          </div>
        </section>

        {/* ==================================================================
            CHAPTER 02: FROM CODE TO CONTAINER (Exploded Technical View)
            ================================================================== */}
        <section id="chapter-container" className={`scrolly-chapter scrolly-chapter-right ${activeChapter === 2 ? 'chapter-active' : ''}`}>
          <div className="scrolly-card-panel">
            <div className="section-badge-row">
              <span className="section-index-num">02</span>
              <span className="section-dash-line" />
              <span className="section-micro-tag">CONTAINER PIPELINE</span>
            </div>

            <h2 className="editorial-heading">
              From Code <br />
              <span className="text-white-bright">to Container.</span>
            </h2>

            <p className="editorial-subcopy">
              Auto-generated multi-stage Dockerfiles tailored for fast inference with up to 70% smaller container footprint.
            </p>

            <div className="editorial-bullets-list">
              <div className="bullet-clean-item">
                <span className="bullet-bullet-cyan">•</span>
                <span>Zero Docker knowledge required — fully automated build</span>
              </div>
              <div className="bullet-clean-item">
                <span className="bullet-bullet-cyan">•</span>
                <span>Optimized CUDA runtime with automatic healthcheck verification</span>
              </div>
            </div>
          </div>
        </section>

        {/* ==================================================================
            CHAPTER 03: SHARE WITH THE WORLD (Network Conduits)
            ================================================================== */}
        <section id="chapter-share" className={`scrolly-chapter scrolly-chapter-left ${activeChapter === 3 ? 'chapter-active' : ''}`}>
          <div className="scrolly-card-panel">
            <div className="section-badge-row">
              <span className="section-index-num">03</span>
              <span className="section-dash-line" />
              <span className="section-micro-tag">GLOBAL DISTRIBUTION</span>
            </div>

            <h2 className="editorial-heading">
              Share with <br />
              <span className="text-white-bright">the World.</span>
            </h2>

            <p className="editorial-subcopy">
              Instant shareable HTTPS endpoints with zero-trust token authentication and automated global edge routing.
            </p>

            <div className="share-url-minimal-pill" onClick={handleCopyUrl}>
              <Link2 size={15} className="text-cyan" />
              <span className="share-url-text">{shareUrl}</span>
              {copiedUrl ? <Check size={14} className="text-cyan" /> : <Copy size={14} />}
            </div>
          </div>
        </section>

        {/* ==================================================================
            CHAPTER 04: IDEAS TO IMPACT (Final Reassembly)
            ================================================================== */}
        <section id="chapter-impact" className={`scrolly-chapter scrolly-chapter-right ${activeChapter === 4 ? 'chapter-active' : ''}`}>
          <div className="scrolly-card-panel">
            <div className="section-badge-row">
              <span className="section-index-num">04</span>
              <span className="section-dash-line" />
              <span className="section-micro-tag">RESEARCH TO PRODUCTION</span>
            </div>

            <h2 className="editorial-heading">
              Ideas <br />
              <span className="text-white-bright">to Impact.</span>
            </h2>

            <p className="editorial-subcopy">
              Eliminating all friction between trained checkpoint weights and live, scalable container endpoints.
            </p>

            <div className="impact-quote-minimal">
              <p className="quote-text">
                "From model checkpoint to live inference in minutes, without infrastructure blockers."
              </p>
            </div>
          </div>
        </section>

        {/* ==================================================================
            FINAL CTA (Side-by-Side: Content Left | 3D Assembled Loop Right)
            ================================================================== */}
        <section id="chapter-cta" className={`scrolly-chapter-cta ${activeChapter >= 5 ? 'chapter-active' : ''}`}>
          <div className="cta-editorial-split-left">
            <div className="cta-micro-tag-row">
              <span className="cta-micro-tag">PRODUCTION READY</span>
            </div>

            <h2 className="cta-headline">
              Build <span className="cta-accent-cyan">Without</span> Limits
            </h2>

            <p className="cta-subcopy">
              Turn your machine learning models into fast, scalable production containers in seconds.
            </p>

            <div className="cta-buttons-group">
              <a href="#chapter-hero" className="btn-cta-primary">
                <span>Get Started</span>
                <ArrowRight size={15} />
              </a>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-cta-secondary"
              >
                <span>Documentation</span>
              </a>
            </div>
          </div>
        </section>
      </div>

      {/* Minimalist Footer with Frame 240 Emblem */}
      <footer className="modelforge-footer">
        <div className="footer-wrapper">
          <div className="footer-top-row">
            <div className="footer-brand-col">
              <div className="footer-logo">
                <img src={logoFrame240} alt="ModelForge" className="footer-frame240-logo" />
                <span className="brand-text">
                  Model<span className="brand-accent">Forge</span>
                </span>
              </div>
              <div className="footer-workflow-tag">
                ZIP <span className="arrow">→</span> CONTAINER <span className="arrow">→</span> SHARE
              </div>
            </div>

            <nav className="footer-nav-col" aria-label="Footer Navigation">
              <ul className="footer-links-list">
                <li><a href="#chapter-hero" className="footer-link">About</a></li>
                <li><a href="#chapter-unpack" className="footer-link">Docs</a></li>
                <li><a href="#chapter-container" className="footer-link">Community</a></li>
                <li><a href="#chapter-share" className="footer-link">Support</a></li>
              </ul>
            </nav>

            <div className="footer-social-col">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="social-icon-link" aria-label="GitHub">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
              </a>
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="social-icon-link" aria-label="LinkedIn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                </svg>
              </a>
              <a href="https://x.com" target="_blank" rel="noopener noreferrer" className="social-icon-link" aria-label="X">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
            </div>
          </div>

          <div className="footer-bottom-row">
            <p className="copyright-text">
              © 2025 ModelForge. Built for a smarter tomorrow.
            </p>
          </div>
        </div>
      </footer>

      {/* Apple Toast Notification */}
      {toastMessage && (
        <div className="apple-toast-pill" role="status" aria-live="polite">
          <div className="toast-dot" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
