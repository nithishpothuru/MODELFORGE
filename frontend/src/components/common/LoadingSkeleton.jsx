import React from 'react';

export function Skeleton({ className = '', height = '20px', width = '100%' }) {
  return (
    <div
      className={`mf-skeleton ${className}`}
      style={{ height, width }}
      aria-hidden="true"
    />
  );
}

export function ProjectCardSkeleton() {
  return (
    <div className="mf-project-card-skeleton">
      <div className="skeleton-header">
        <Skeleton width="60%" height="22px" />
        <Skeleton width="65px" height="20px" className="rounded-full" />
      </div>
      <Skeleton width="90%" height="14px" className="mt-3" />
      <Skeleton width="40%" height="14px" className="mt-2" />
      <div className="skeleton-footer mt-5">
        <Skeleton width="30%" height="16px" />
        <Skeleton width="24px" height="24px" className="rounded" />
      </div>
    </div>
  );
}

const LoadingSkeleton = {
  Skeleton,
  ProjectCardSkeleton,
};

export default LoadingSkeleton;
