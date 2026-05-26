/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts}',
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#0c8599',
          light: '#e3fafc',
          hover: '#0b7285',
        },
        success: '#2f9e44',
        warning: '#e07b39',
        error: '#c92a2a',
        bg: {
          primary: '#ffffff',
          secondary: '#f8f9fa',
          reading: '#fefefe',
          hover: '#f1f3f5',
        },
        border: {
          light: '#e9ecef',
          base: '#dee2e6',
        },
        text: {
          primary: '#212529',
          secondary: '#495057',
          muted: '#868e96',
        },
      },
      fontFamily: {
        body: ['"PingFang SC"', '"HarmonyOS Sans"', '"Microsoft YaHei"', '"Noto Serif SC"', '"STSong"', '"SimSun"', 'serif'],
        ui: ['"PingFang SC"', '"HarmonyOS Sans"', '"Microsoft YaHei"', '-apple-system', 'sans-serif'],
        mono: ['"Cascadia Code"', '"Fira Code"', '"Consolas"', '"Monaco"', 'monospace'],
      },
      borderRadius: {
        sm: '6px',
        md: '8px',
        lg: '12px',
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(0,0,0,0.04)',
        'md': '0 4px 12px rgba(0,0,0,0.06)',
        'lg': '0 8px 24px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}
