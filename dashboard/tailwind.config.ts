import type { Config } from "tailwindcss";

// Colour is bound to design tokens (H.6.1). The palette intentionally exposes
// ONLY surface/text tokens plus the three signal colours; there is no
// decorative accent, so a stray coloured element cannot slip in unnoticed.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--fg-canvas)",
        raised: "var(--fg-raised)",
        hairline: "var(--fg-hairline)",
        text: "var(--fg-text)",
        muted: "var(--fg-muted)",
        blocked: "var(--fg-blocked)",
        masked: "var(--fg-masked)",
        shadow: "var(--fg-shadow)",
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        xs: ["12px", { lineHeight: "16px" }],
        sm: ["14px", { lineHeight: "20px" }],
        base: ["16px", { lineHeight: "24px" }],
        lg: ["20px", { lineHeight: "28px" }],
        xl: ["28px", { lineHeight: "34px" }],
      },
    },
  },
  plugins: [],
};

export default config;
