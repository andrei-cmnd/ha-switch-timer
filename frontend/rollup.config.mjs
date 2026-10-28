import nodeResolve from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";
import esbuild from "rollup-plugin-esbuild";

// `npm run watch` sets DEV: unminified output with source maps.
const dev = Boolean(process.env.DEV);

export default {
  input: "src/switch-timer-card.ts",
  output: {
    file: "../custom_components/switch_timer/frontend/switch-timer-card.js",
    format: "es",
    sourcemap: dev,
    inlineDynamicImports: true,
  },
  plugins: [
    nodeResolve(),
    // Transpile only; type checking is `npm run typecheck`.
    esbuild({ target: "es2022" }),
    !dev && terser({ format: { comments: false } }),
  ],
  watch: { clearScreen: false },
};
