interface VeridianLogoProps {
  className?: string;
  variant?: 'full' | 'icon';
  white?: boolean;
}

export default function VeridianLogo({ className = '', variant = 'full', white = false }: VeridianLogoProps) {
  const textColor = white ? '#FFFFFF' : '#059669';
  const iconColor = white ? '#FFFFFF' : '#059669';

  if (variant === 'icon') {
    return (
      <svg
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
      >
        {/* V-shaped icon */}
        <path
          d="M8 6L20 32L32 6"
          stroke={iconColor}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M12 6L20 22L28 6"
          stroke={iconColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.5"
        />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 180 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* V-shaped icon */}
      <path
        d="M8 6L20 32L32 6"
        stroke={iconColor}
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 6L20 22L28 6"
        stroke={iconColor}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />
      
      {/* VERIDIAN text */}
      <text
        x="44"
        y="26"
        fill={textColor}
        style={{ fontSize: '20px', fontWeight: '700', letterSpacing: '0.5px' }}
      >
        VERIDIAN
      </text>
    </svg>
  );
}
