/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "media",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Schibsted Grotesk", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["Newsreader", "ui-serif", "Georgia", "serif"],
      },
      colors: {
        // The single accent: deep pine ink (replaces the default indigo everywhere).
        indigo: {
          50: "#eef5f2", 100: "#d5e8e0", 200: "#abd1c2", 300: "#7bb59f", 400: "#4b937a",
          500: "#2d7760", 600: "#1f6250", 700: "#194e40", 800: "#143f34", 900: "#10332a", 950: "#0a2019",
        },
        stone: {
          50: "#f6f6f3", 100: "#ecece8", 200: "#dfdfda", 300: "#c8c8c2", 400: "#9c9c95",
          500: "#73736d", 600: "#57574f", 700: "#41413b", 800: "#2a2a26", 900: "#1c1c19", 950: "#121210",
        },
      },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "none" } },
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-left": { from: { transform: "translateX(24px)", opacity: "0" }, to: { transform: "none", opacity: "1" } },
        pop: { from: { transform: "scale(.97)", opacity: "0" }, to: { transform: "none", opacity: "1" } },
      },
      animation: {
        rise: "rise .2s ease-out",
        "fade-in": "fade-in .15s ease-out",
        "slide-left": "slide-left .2s ease-out",
        pop: "pop .15s ease-out",
      },
    },
  },
  plugins: [],
};
