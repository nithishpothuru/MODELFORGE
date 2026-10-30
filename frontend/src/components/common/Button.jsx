import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  leftIcon = null,
  rightIcon = null,
  type = 'button',
  onClick,
  className = '',
  ...props
}) {
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      onClick={onClick}
      className={`mf-btn mf-btn-${variant} mf-btn-${size} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 size={size === 'sm' ? 14 : 16} className="mf-btn-spinner animate-spin" />
      ) : (
        leftIcon && <span className="mf-btn-icon-left">{leftIcon}</span>
      )}
      <span className="mf-btn-text">{children}</span>
      {!loading && rightIcon && <span className="mf-btn-icon-right">{rightIcon}</span>}
    </button>
  );
}

