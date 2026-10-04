/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['"DM Sans"', 'sans-serif'] },
      colors: {
        bg:      '#F0F4F8',
        card:    '#FFFFFF',
        accent:  '#0ABFBC',
        adark:   '#089F9D',
        tmain:   '#0D2D2D',
        tsub:    '#557272',   // 5.2:1 on white (WCAG AA)
        border:  '#E4F0F0',
        coral:   '#F27C7C',
        success: '#36C98E',
        amber:   '#F5A623',
        blue:    '#5BA4CF',
        sidebar: '#0D2D2D',
        // Text-safe (>= 4.5:1 on white) variants of the status colours
        'coral-ink':   '#B83A38',
        'amber-ink':   '#9A5B00',
        'success-ink': '#127552',
        'accent-ink':  '#087F7D',
      },
      borderRadius: { card: '20px', pill: '999px' },
      boxShadow: {
        card:  '0 2px 12px 0 rgba(10,191,188,0.07)',
        hover: '0 6px 24px 0 rgba(10,191,188,0.16)',
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
