interface GeminiLogoProps {
  size?: number;
  className?: string;
}

export const GeminiLogo: React.FC<GeminiLogoProps> = ({ size = 24, className = "" }) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 48 48" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        {/* Gradiente para a ponta superior (azul claro) */}
        <linearGradient id="gemini-top" x1="24" y1="2" x2="24" y2="24" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4A8CF7" />
          <stop offset="100%" stopColor="#6BA3F9" />
        </linearGradient>
        {/* Gradiente para a ponta direita (azul médio) */}
        <linearGradient id="gemini-right" x1="46" y1="24" x2="24" y2="24" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4A8CF7" />
          <stop offset="100%" stopColor="#6BA3F9" />
        </linearGradient>
        {/* Gradiente para a ponta inferior (azul/roxo) */}
        <linearGradient id="gemini-bottom" x1="24" y1="46" x2="24" y2="24" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#8B7EC8" />
          <stop offset="100%" stopColor="#6BA3F9" />
        </linearGradient>
        {/* Gradiente para a ponta esquerda (azul/roxo claro) */}
        <linearGradient id="gemini-left" x1="2" y1="24" x2="24" y2="24" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#8B7EC8" />
          <stop offset="100%" stopColor="#6BA3F9" />
        </linearGradient>
      </defs>
      {/* Estrela de 4 pontas do Gemini - maior e com cores corretas */}
      <path 
        d="M24 2 L28 20 L24 24 L20 20 Z" 
        fill="url(#gemini-top)" 
      />
      <path 
        d="M46 24 L28 28 L24 24 L28 20 Z" 
        fill="url(#gemini-right)" 
      />
      <path 
        d="M24 46 L20 28 L24 24 L28 28 Z" 
        fill="url(#gemini-bottom)" 
      />
      <path 
        d="M2 24 L20 20 L24 24 L20 28 Z" 
        fill="url(#gemini-left)" 
      />
    </svg>
  );
};
