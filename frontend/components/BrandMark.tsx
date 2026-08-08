// Raksha AI brand mark — a protective shield with an ECG pulse. The
// heartbeat line is the identity motif shared with the mobile app.
export function BrandMark({
  size = 32,
  light = false,
}: {
  size?: number;
  light?: boolean;
}) {
  const line = light ? '#04100d' : '#e9f5f0';
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden>
      <defs>
        <linearGradient id="raksha-shield" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#0d9488" />
          <stop offset="1" stopColor="#0f766e" />
        </linearGradient>
      </defs>
      <path
        d="M24 3.2l15.6 5.8v11.4c0 9.3-6.3 16.4-15.6 21.8C14.7 36.8 8.4 29.7 8.4 20.4V9L24 3.2z"
        fill="url(#raksha-shield)"
        stroke="#2dd4bf"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M12.5 24.5h5.2l2.2-4.6 3.4 8.6 2.4-6.2 1.9 3 1.9-0.8h6"
        stroke={line}
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M15 27.8h18"
        stroke={line}
        strokeWidth="1.4"
        strokeOpacity="0.55"
        strokeLinecap="round"
      />
    </svg>
  );
}
