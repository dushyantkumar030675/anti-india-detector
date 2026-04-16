import clsx from 'clsx';

const MAP = {
  low:      'badge-low',
  medium:   'badge-medium',
  high:     'badge-high',
  critical: 'badge-critical',
};

export default function SeverityBadge({ severity }) {
  return (
    <span className={clsx(MAP[severity] || 'badge-low')}>
      {severity}
    </span>
  );
}
