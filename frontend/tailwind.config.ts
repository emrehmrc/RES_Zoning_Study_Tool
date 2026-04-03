import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        solar: { DEFAULT: '#FF9F1C', dark: '#CC7A00', light: '#FFEBD0' },
        onshore: { DEFAULT: '#00008B', dark: '#000060', light: '#D0D0FF' },
        offshore: { DEFAULT: '#1E90FF', dark: '#104E8B', light: '#D0EBFF' },
      },
    },
  },
  plugins: [],
}

export default config
