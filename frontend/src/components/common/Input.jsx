import React, { forwardRef } from 'react';

const Input = forwardRef(function Input(
  {
    label,
    error,
    hint,
    id,
    type = 'text',
    leftIcon = null,
    rightAction = null,
    className = '',
    required = false,
    ...props
  },
  ref
) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={`mf-input-group ${className}`}>
      {label && (
        <label htmlFor={inputId} className="mf-input-label">
          {label} {required && <span className="text-[#00D6FF]">*</span>}
        </label>
      )}

      <div className={`mf-input-wrapper ${error ? 'has-error' : ''}`}>
        {leftIcon && <span className="mf-input-left-icon">{leftIcon}</span>}

        <input
          id={inputId}
          ref={ref}
          type={type}
          required={required}
          className={`mf-input-field ${leftIcon ? 'with-left-icon' : ''} ${
            rightAction ? 'with-right-action' : ''
          }`}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          {...props}
        />

        {rightAction && <div className="mf-input-right-action">{rightAction}</div>}
      </div>

      {error && (
        <p id={`${inputId}-error`} className="mf-input-error-msg" role="alert">
          {error}
        </p>
      )}

      {!error && hint && (
        <p id={`${inputId}-hint`} className="mf-input-hint-msg">
          {hint}
        </p>
      )}
    </div>
  );
});

export default Input;

