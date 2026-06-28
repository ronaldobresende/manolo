/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Paleta clínica: verde musgo + bege quente
        primary: {
          DEFAULT: '#2D6A4F',
          50:  '#F0F7F4',
          100: '#D8EDE5',
          200: '#B2D9CB',
          300: '#8AC4B1',
          400: '#52B788',
          500: '#2D6A4F',
          600: '#245740',
          700: '#1B4330',
          800: '#132F22',
          900: '#0A1B13',
        },
        accent: {
          DEFAULT: '#52B788',
          light: '#95D5B2',
          muted: '#B7E4C7',
        },
        neutral: {
          bg:      '#F8F5F0',   // fundo principal — bege quente
          surface: '#FFFFFF',   // cards e modais
          border:  '#E8E4DE',   // bordas suaves
        },
        manolo: {
          text:    '#1B2D27',   // verde quase preto
          muted:   '#6B7F78',   // labels, metadata
          danger:  '#B5451B',   // alertas, crises
          warning: '#D4792A',   // atenção
          success: '#2D6A4F',   // positivo
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'card': '12px',
        'pill': '999px',
      },
      boxShadow: {
        'card':  '0 1px 4px rgba(27, 45, 39, 0.08), 0 4px 16px rgba(27, 45, 39, 0.04)',
        'card-hover': '0 4px 12px rgba(27, 45, 39, 0.12), 0 8px 24px rgba(27, 45, 39, 0.06)',
        'sidebar': '2px 0 16px rgba(27, 45, 39, 0.06)',
      },
      animation: {
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
}
