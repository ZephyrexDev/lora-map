import pluginVue from "eslint-plugin-vue";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import vueParser from "vue-eslint-parser";

/** Shared rules applied to both .ts and .vue files. */
const sharedRules = {
  // TypeScript
  "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  "@typescript-eslint/no-explicit-any": "warn",
  "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports" }],
  "@typescript-eslint/no-non-null-assertion": "warn",
  "@typescript-eslint/no-shadow": "error",
  "@typescript-eslint/no-floating-promises": "error",
  "@typescript-eslint/require-await": "warn",

  // Core JS
  "no-var": "error",
  "prefer-const": "error",
  "prefer-template": "error",
  "no-console": ["warn", { allow: ["warn", "error"] }],
  "no-debugger": "error",
  "no-alert": "warn",
  "no-await-in-loop": "warn",
  eqeqeq: ["error", "always"],
  curly: ["error", "multi-line"],
  "no-throw-literal": "error",
  "no-implicit-coercion": "error",
  "no-param-reassign": ["error", { props: false }],
  "no-nested-ternary": "error",
  "no-return-assign": "error",
  "no-self-compare": "error",
  "no-useless-concat": "error",
  "object-shorthand": "error",
  "prefer-arrow-callback": "error",
  "prefer-destructuring": ["error", { object: true, array: false }],
  "prefer-rest-params": "error",
  "prefer-spread": "error",
};

/** Type-aware parser options shared between .ts and .vue configs. */
const typeAwareParserOptions = {
  ecmaVersion: "latest",
  sourceType: "module",
  project: "./tsconfig.app.json",
};

export default [
  {
    ignores: ["dist/", "app/ui/", "node_modules/", ".venv/"],
  },
  {
    files: ["src/**/*.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: typeAwareParserOptions,
    },
    plugins: {
      "@typescript-eslint": tseslint,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...sharedRules,
    },
  },
  {
    files: ["src/**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ...typeAwareParserOptions,
        extraFileExtensions: [".vue"],
      },
    },
    plugins: {
      vue: pluginVue,
      "@typescript-eslint": tseslint,
    },
    rules: {
      ...pluginVue.configs["vue3-recommended"].rules,
      ...sharedRules,

      // Vue-specific
      "vue/no-unused-refs": "error",
      "vue/no-useless-v-bind": "error",
      "vue/no-v-html": "warn",
      "vue/prefer-true-attribute-shorthand": "error",
      "vue/component-name-in-template-casing": ["error", "PascalCase"],
      "vue/define-macros-order": ["error", { order: ["defineProps", "defineEmits"] }],
      "vue/no-template-shadow": "error",
      "vue/block-order": ["error", { order: ["template", "script", "style"] }],
      "vue/eqeqeq": ["error", "always"],
    },
  },
];
