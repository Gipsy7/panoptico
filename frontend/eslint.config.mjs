import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jsxA11y from "eslint-plugin-jsx-a11y";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Acessibilidade no conjunto strict (o plugin já é registrado pelo Next).
  { rules: { ...jsxA11y.flatConfigs.strict.rules } },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Relatórios do Playwright (npm run e2e).
    "e2e-relatorio/**",
    "test-results/**",
    "playwright-report/**",
  ]),
]);

export default eslintConfig;
