import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Verdict colors
        "verdict-strong-buy": "#16a34a",
        "verdict-buy": "#2563eb",
        "verdict-hold": "#d97706",
        "verdict-skip": "#dc2626",
      },
    },
  },
  plugins: [],
};

export default config;
