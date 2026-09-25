import React, { useState, useEffect } from 'react';
import { Copy, Check, ChevronDown, ChevronUp, Sparkles, FileCode } from 'lucide-react';

const CODE_SNIPPETS = {
  pipeline: {
    filename: 'pipeline.py',
    tag: 'Python AST',
    chapter: 1,
    content: `import torch
from transformers import AutoModelForCausalLM

# ModelForge auto-extracts AST & CUDA bindings
model = AutoModelForCausalLM.from_pretrained(
    "modelforge/neural-engine",
    torch_dtype=torch.float16,
    device_map="auto"
)`,
  },
  dockerfile: {
    filename: 'Dockerfile',
    tag: 'CUDA Container',
    chapter: 2,
    content: `FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`,
  },
};

export default function DockedCodePreview({ activeChapter = 0, scrollProgress = 0 }) {
  const [activeTab, setActiveTab] = useState('pipeline');
  const [copied, setCopied] = useState(false);
  const [minimized, setMinimized] = useState(() => {
    return typeof window !== 'undefined' ? window.innerWidth <= 860 : false;
  });
  const [sectionProgress, setSectionProgress] = useState(0);

  // Auto-minimize on small viewports
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 860) {
        setMinimized(true);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Automatically switch tab based on active chapter
  useEffect(() => {
    if (activeChapter === 2) {
      setActiveTab('dockerfile');
    } else {
      setActiveTab('pipeline');
    }
  }, [activeChapter]);

  // Real-time scroll listener computing exact user position inside the active section
  useEffect(() => {
    const updateProgress = () => {
      if (activeChapter !== 1 && activeChapter !== 2) return;
      const targetId = activeChapter === 1 ? 'chapter-unpack' : 'chapter-container';
      const el = document.getElementById(targetId);
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      // Start as section approaches center; complete as section passes center
      const travel = rect.height;
      const scrolled = (windowHeight * 0.7) - rect.top;
      const pct = Math.min(100, Math.max(0, Math.round((scrolled / travel) * 100)));
      setSectionProgress(pct);
    };

    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();
    return () => window.removeEventListener('scroll', updateProgress);
  }, [activeChapter]);

  // Only visible where required (Section 01 and Section 02)
  const isVisible = activeChapter === 1 || activeChapter === 2;

  const handleCopy = () => {
    const text = CODE_SNIPPETS[activeTab]?.content || '';
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const currentSnippet = CODE_SNIPPETS[activeTab] || CODE_SNIPPETS.pipeline;

  return (
    <div
      className={`docked-code-container ${
        isVisible ? 'docked-code-visible' : 'docked-code-hidden'
      } ${minimized ? 'docked-code-minimized' : ''}`}
      aria-label="Interactive Code Inspector"
      aria-hidden={!isVisible}
    >
      {/* Scroll-Driven Glowing Progress Bar */}
      <div className="docked-code-progressbar-track">
        <div
          className="docked-code-progressbar-fill"
          style={{ width: `${sectionProgress}%` }}
        />
      </div>

      {/* Header with Tabs and Actions */}
      {/* <div className="docked-code-header">
        <div className="docked-code-tabs">
          {Object.keys(CODE_SNIPPETS).map((key) => {
            const item = CODE_SNIPPETS[key];
            const isActive = activeTab === key;
            return (
              <button
                key={key}
                className={`docked-tab-btn ${isActive ? 'docked-tab-active' : ''}`}
                onClick={() => setActiveTab(key)}
              >
                <FileCode size={11} className="tab-icon" />
                <span>{item.filename}</span>
              </button>
            );
          })}
        </div>

        <div className="docked-code-actions">
          <button
            className="docked-action-btn"
            onClick={handleCopy}
            title="Copy Code"
            aria-label="Copy Code"
          >
            {copied ? <Check size={12} className="text-cyan" /> : <Copy size={12} />}
          </button>

          <button
            className="docked-action-btn"
            onClick={() => setMinimized(!minimized)}
            title={minimized ? 'Expand Code' : 'Minimize Code'}
            aria-label={minimized ? 'Expand Code' : 'Minimize Code'}
          >
            {minimized ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
      </div> */}

      {/* Code Body */}
      {/* {!minimized && (
        <div className="docked-code-body">
          <div className="docked-code-tag-row">
            <span className="docked-code-tag">
              <Sparkles size={10} className="sparkle-amber" />
              {currentSnippet.tag}
            </span>
            <span className="docked-code-speed">Scroll: {sectionProgress}%</span>
          </div>

          <pre className="docked-pre">
            <code>
              {currentSnippet.content.split('\n').map((line, idx) => (
                <div key={idx} className="code-line">
                  <span className="line-num">{idx + 1}</span>
                  <span className="line-text">{formatSyntax(line)}</span>
                </div>
              ))}
            </code>
          </pre>
        </div>
      )} */}
    </div>
  );
}

// Simple syntax colorizer for keywords and comments
function formatSyntax(line) {
  if (line.trim().startsWith('#')) {
    return <span className="syntax-comment">{line}</span>;
  }
  return <span>{line}</span>;
}
