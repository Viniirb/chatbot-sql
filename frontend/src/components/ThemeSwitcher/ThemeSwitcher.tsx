import { useEffect, useState } from "react";

type Theme = 'theme-neutral' | 'theme-blue' | 'theme-green' | 'theme-purple';

export const ThemeSwitcher = () => {
  const [theme, setTheme] = useState<Theme>(() => {
    return (localStorage.getItem('chat_theme') as Theme) || 'theme-neutral';
  });

  useEffect(() => {
    document.body.className = '';
    document.body.classList.add(theme);
    localStorage.setItem('chat_theme', theme);
  }, [theme]);

  return (
    <div className="flex items-center space-x-2">
      <button aria-label="Set Neutral Theme" onClick={() => setTheme('theme-neutral')} className="w-5 h-5 rounded-full bg-gray-500 ring-2 ring-offset-2 ring-offset-gray-900 ring-transparent focus:outline-none focus:ring-white"></button>
      <button aria-label="Set Blue Theme" onClick={() => setTheme('theme-blue')} className="w-5 h-5 rounded-full bg-blue-600 ring-2 ring-offset-2 ring-offset-gray-900 ring-transparent focus:outline-none focus:ring-white"></button>
      <button aria-label="Set Green Theme" onClick={() => setTheme('theme-green')} className="w-5 h-5 rounded-full bg-green-800 ring-2 ring-offset-2 ring-offset-gray-900 ring-transparent focus:outline-none focus:ring-white"></button>
      <button aria-label="Set Purple Theme" onClick={() => setTheme('theme-purple')} className="w-5 h-5 rounded-full bg-purple-600 ring-2 ring-offset-2 ring-offset-gray-900 ring-transparent focus:outline-none focus:ring-white"></button>
    </div>
  );
};