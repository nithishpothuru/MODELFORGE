import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

export default function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'max-w-lg',
  showClose = true,
}) {
  const modalRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onCloseRef.current?.();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';

    // Focus initial input only once when modal opens, and only if not already focusing an element inside
    const focusTimer = setTimeout(() => {
      if (modalRef.current && !modalRef.current.contains(document.activeElement)) {
        const initialFocusable = modalRef.current.querySelector(
          'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])'
        );
        if (initialFocusable) {
          initialFocusable.focus();
        }
      }
    }, 50);

    return () => {
      clearTimeout(focusTimer);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="mf-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-headline"
    >
      <div ref={modalRef} className={`mf-modal-container ${maxWidth}`}>
        {(title || showClose) && (
          <div className="mf-modal-header">
            <div>
              {title && (
                <h3 id="modal-headline" className="mf-modal-title">
                  {title}
                </h3>
              )}
              {subtitle && <p className="mf-modal-subtitle">{subtitle}</p>}
            </div>
            {showClose && (
              <button
                type="button"
                className="mf-modal-close-btn"
                onClick={onClose}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        <div className="mf-modal-body">{children}</div>
      </div>
    </div>
  );
}

