import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      borderWidth: {
        thin: "1px",
      },
      borderRadius: {
        lg: "10px",
        md: "8px",
        sm: "6px",
        xl: "12px",
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.03)",
        card: "0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.02)",
        elevated: "0 4px 12px -2px rgb(0 0 0 / 0.06), 0 2px 6px -2px rgb(0 0 0 / 0.03)",
        popover: "0 8px 24px -4px rgb(0 0 0 / 0.08), 0 4px 8px -4px rgb(0 0 0 / 0.04)",
        input: "0 0 0 3px rgb(9 105 218 / 0.08)",
      },
    },
  },
} satisfies Config;
