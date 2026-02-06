/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './src/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    50: '#ededff',
                    100: '#dddcff',
                    200: '#bfbbff',
                    300: '#9c95ff',
                    400: '#7d73ff',
                    500: '#6C63FF',
                    600: '#5a4fff',
                    700: '#4a3de6',
                    800: '#3c32b8',
                    900: '#332d91',
                },
                surface: {
                    0: '#000000',
                    50: '#0a0a0a',
                    100: '#111111',
                    200: '#1a1a1a',
                    300: '#222222',
                    400: '#2a2a2a',
                    500: '#333333',
                    600: '#444444',
                    700: '#555555',
                    800: '#888888',
                    900: '#aaaaaa',
                },
                severity: {
                    critical: '#FF3B30',
                    high: '#FF9500',
                    medium: '#FFCC00',
                    low: '#34C759',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
            },
            animation: {
                'slide-up': 'slideUp 0.3s ease-out',
                'slide-down': 'slideDown 0.3s ease-out',
                'fade-in': 'fadeIn 0.2s ease-out',
                'pulse-dot': 'pulseDot 2s infinite',
                'shimmer': 'shimmer 1.5s infinite',
            },
            keyframes: {
                slideUp: { '0%': { transform: 'translateY(12px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
                slideDown: { '0%': { transform: 'translateY(-12px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
                fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
                pulseDot: { '0%, 100%': { opacity: '1' }, '50%': { opacity: '0.3' } },
                shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
            },
        },
    },
    plugins: [],
};
