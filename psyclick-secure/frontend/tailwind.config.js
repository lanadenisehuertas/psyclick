/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['"DM Sans Variable"', '"DM Sans"', 'system-ui', 'sans-serif'],
        display: ['"Schibsted Grotesk Variable"', '"DM Sans Variable"', 'sans-serif'],
        mono:    ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        bg:      '#F2F7F8',
        card:    '#FFFFFF',
        accent:  '#0ABFBC',
        adark:   '#089F9D',
        tmain:   '#0F2A33',
        tsub:    '#4A6670',   // 6.1:1 on white (WCAG AA)
        border:  '#D9E6EA',
        coral:   '#F27C7C',
        success: '#36C98E',
        amber:   '#F5A623',
        blue:    '#5BA4CF',
        sidebar: '#0F2A33',
        // Logo palette (light tints: surfaces and data, never text on white)
        mint:    '#70E8C0',
        cyan:    '#68D8E8',
        peri:    '#78A8D8',
        'peri-ink': '#3D5FA8',
        // Text-safe (>= 4.5:1 on white) variants of the status colours
        'coral-ink':   '#B83A38',
        'amber-ink':   '#9A5B00',
        'success-ink': '#127552',
        'accent-ink':  '#0A6B80',
      },
      borderRadius: { card: '20px', pill: '999px' },
      backgroundImage: { brand: 'linear-gradient(115deg, #70E8C0 0%, #68D8E8 48%, #78A8D8 100%)' },
      boxShadow: {
        card:  '0 1px 2px rgba(15,42,51,0.05), 0 6px 20px -8px rgba(15,42,51,0.12), inset 0 1px 0 rgba(255,255,255,0.8)',
        hover: '0 2px 4px rgba(15,42,51,0.06), 0 18px 36px -14px rgba(15,42,51,0.24), inset 0 1px 0 rgba(255,255,255,0.8)',
        modal: '0 20px 60px 0 rgba(13,45,45,0.18)',
      },
      transitionDuration: { DEFAULT: '200ms' },
      animation: {
        'fade-in':     'fadeIn 0.4s ease-out both',
        'slide-up':    'slideUp 0.45s ease-out both',
        'slide-right': 'slideRight 0.5s ease-out both',
        'fade-up-1':   'fadeUp 0.5s 0.1s ease-out both',
        'fade-up-2':   'fadeUp 0.5s 0.25s ease-out both',
        'fade-up-3':   'fadeUp 0.5s 0.4s ease-out both',
        'float':       'float 3s ease-in-out infinite',
        'pulse-slow':  'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'shimmer':     'shimmer 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:    { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:   { from: { opacity: 0, transform: 'translateY(18px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideRight:{ from: { opacity: 0, transform: 'translateX(-24px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
        fadeUp:    { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        float:     { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-8px)' } },
        shimmer:   { '0%,100%': { opacity: 0.6 }, '50%': { opacity: 1 } },
      },
    },
  },
  plugins: [],
}
