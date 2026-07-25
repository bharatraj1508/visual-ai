import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./containers/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#FB676E",
        secondary: "#1F2937",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
