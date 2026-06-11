import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: "#176B45",
        limeLine: "#D8F45D",
        bootBlack: "#111827",
      },
    },
  },
  plugins: [],
};

export default config;
