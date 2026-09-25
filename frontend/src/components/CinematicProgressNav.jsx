import React, { useState, useEffect } from 'react';

const CHAPTERS = [
  { id: 'chapter-hero', index: '00', label: 'HERO', title: 'Assembled Core' },
  { id: 'chapter-unpack', index: '01', label: 'UNPACK', title: 'Project Decomposition' },
  { id: 'chapter-container', index: '02', label: 'CONTAINER', title: 'Code to Container' },
  { id: 'chapter-share', index: '03', label: 'SHARE', title: 'Global Network' },
  { id: 'chapter-impact', index: '04', label: 'IMPACT', title: 'Ideas to Impact' },
];

export default function CinematicProgressNav({ activeChapter = 0, scrollProgress = 0 }) {
  const [scrolledPastHero, setScrolledPastHero] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      // Appear smoothly after user scrolls past hero
      setScrolledPastHero(window.scrollY > 60);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToChapter = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // 14 ticks across the horizontal bar with active glowing indicator
  const TICK_COUNT = 15;
  const activeTickIndex = Math.min(
    TICK_COUNT - 1,
    Math.max(0, Math.round(scrollProgress * (TICK_COUNT - 1)))
  );

  return (
    <nav
      className={`cinematic-progress-nav ${
        scrolledPastHero ? 'cinematic-nav-visible' : 'cinematic-nav-hidden'
      }`}
      aria-label="Cinematic Chapter Navigation"
      aria-hidden={!scrolledPastHero}
    >
      {/* Top Chapter Pills */}
      <div className="cinematic-nav-chapters">
        {CHAPTERS.map((ch, idx) => {
          const isActive = activeChapter === idx;
          return (
            <button
              key={ch.id}
              className={`cinematic-nav-node ${isActive ? 'cinematic-node-active' : ''}`}
              onClick={() => scrollToChapter(ch.id)}
              title={`${ch.index} ${ch.title}`}
              aria-label={`Jump to ${ch.label}`}
            >
              <span className="cinematic-node-index">{ch.index}</span>
              <span className="cinematic-node-label">{ch.label}</span>
            </button>
          );
        })}
      </div>

      {/* Cinematic Horizontal Tick Marks & Active Glowing Slider */}
      <div className="cinematic-tick-track">
        {Array.from({ length: TICK_COUNT }).map((_, i) => {
          const isActive = i === activeTickIndex;
          const isPassed = i < activeTickIndex;
          return (
            <div
              key={i}
              className={`cinematic-tick ${isActive ? 'tick-active' : ''} ${
                isPassed ? 'tick-passed' : ''
              }`}
            >
              {isActive && <span className="tick-glow-orb" />}
            </div>
          );
        })}
        {/* Continuous gradient progress line underneath */}
        <div
          className="cinematic-tick-fill"
          style={{ width: `${Math.round(scrollProgress * 100)}%` }}
        />
      </div>
    </nav>
  );
}
