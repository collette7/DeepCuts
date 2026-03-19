import './SkeletonCard.scss';

export default function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton-image" />
      <div className="skeleton-info">
        <div className="skeleton-title" />
        <div className="skeleton-artist" />
        <div className="skeleton-meta" />
      </div>
    </div>
  );
}
