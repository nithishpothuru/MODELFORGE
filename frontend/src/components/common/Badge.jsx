import React from 'react';

export default function Badge({ status = 'created', children, size = 'sm', className = '' }) {
  const normStatus = (status || '').toLowerCase();

  let variant = 'default';
  let dotColor = '#888';

  if (normStatus === 'passed' || normStatus === 'active' || normStatus === 'validated' || normStatus === 'online' || normStatus === 'ok' || normStatus === 'deployed' || normStatus === 'running') {
    variant = 'success';
    dotColor = '#10B981';
  } else if (normStatus === 'failed' || normStatus === 'validation_failed' || normStatus === 'error') {
    variant = 'danger';
    dotColor = '#EF4444';
  } else if (normStatus === 'warning' || normStatus === 'suspended' || normStatus === 'stopped') {
    variant = 'warning';
    dotColor = '#F59E0B';
  } else if (normStatus === 'validating' || normStatus === 'pending') {
    variant = 'info';
    dotColor = '#00D6FF';
  } else if (normStatus === 'uploaded') {
    variant = 'cyan';
    dotColor = '#00D6FF';
  }

  const baseStyles = 'inline-flex items-center font-medium rounded-full border transition-colors';
  const sizeStyles = size === 'xs' 
    ? 'text-[11px] px-2 py-0.5 gap-1.5' 
    : size === 'md' 
    ? 'text-xs px-3 py-1 gap-2' 
    : 'text-xs px-2.5 py-0.5 gap-1.5';

  const variantStyles = {
    default: 'bg-white/[0.04] text-white/70 border-white/10',
    cyan: 'bg-[#00D6FF]/10 text-[#00D6FF] border-[#00D6FF]/30',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    danger: 'bg-red-500/10 text-red-400 border-red-500/30',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    info: 'bg-sky-500/10 text-sky-400 border-sky-500/30 animate-pulse',
  }[variant] || 'bg-white/[0.04] text-white/70 border-white/10';

  return (
    <span className={`mf-badge ${baseStyles} ${sizeStyles} ${variantStyles} ${className}`}>
      <span
        className="mf-badge-dot"
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: dotColor,
          display: 'inline-block',
          boxShadow: `0 0 6px ${dotColor}88`,
        }}
      />
      <span>{children || status}</span>
    </span>
  );
}

