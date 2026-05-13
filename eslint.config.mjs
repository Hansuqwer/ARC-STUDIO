/**
 * ESLint flat configuration for ARC Studio monorepo.
 */
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import prettierConfig from 'eslint-config-prettier';

export default [
    // ── Global ignores ──
    {
        ignores: [
            '**/node_modules/**',
            '**/dist/**',
            '**/lib/**',
            '**/build/**',
            '**/coverage/**',
            '**/*.min.js',
            '**/*.bundle.js',
            '**/src-gen/**',
            '**/tests/e2e/**',
            'eslint.config.mjs',
        ],
    },

    // ── Base recommended rules (non-type-aware) ──
    js.configs.recommended,
    ...tseslint.configs.recommended,
    ...tseslint.configs.stylistic,

    // ── React recommended rules ──
    reactPlugin.configs.flat.recommended,
    reactPlugin.configs.flat['jsx-runtime'],

    // ── React version setting ──
    {
        settings: {
            react: {
                version: '18.0.0',
            },
        },
    },

    // ── Type-aware rules (only for .ts/.tsx) ──
    ...tseslint.configs.recommendedTypeChecked.map(config => ({
        ...config,
        files: ['**/*.ts', '**/*.tsx', '**/*.mts', '**/*.cts'],
    })),

    // ── Custom rule overrides for TS files ──
    {
        files: ['**/*.ts', '**/*.tsx', '**/*.mts', '**/*.cts'],
        plugins: {
            'react-hooks': reactHooksPlugin,
        },
        languageOptions: {
            parserOptions: {
                projectService: true,
            },
        },
        settings: {
            react: {
                version: '18.0.0',
            },
        },
        rules: {
            '@typescript-eslint/no-explicit-any': 'warn',
            '@typescript-eslint/no-unused-vars': [
                'error',
                {
                    argsIgnorePattern: '^_',
                    varsIgnorePattern: '^_',
                },
            ],
            '@typescript-eslint/explicit-function-return-type': 'off',
            '@typescript-eslint/explicit-module-boundary-types': 'off',
            '@typescript-eslint/no-non-null-assertion': 'warn',

            // Unsafe rules: downgrade to off for initial pass (too noisy)
            '@typescript-eslint/no-unsafe-assignment': 'off',
            '@typescript-eslint/no-unsafe-member-access': 'off',
            '@typescript-eslint/no-unsafe-call': 'off',
            '@typescript-eslint/no-unsafe-return': 'off',
            '@typescript-eslint/no-unsafe-argument': 'off',
            '@typescript-eslint/require-await': 'warn',
            '@typescript-eslint/no-base-to-string': 'warn',

            // React
            'react/prop-types': 'off',

            // Theia patterns: floating promises are common (widget.update(), etc.)
            '@typescript-eslint/no-floating-promises': 'warn',
            '@typescript-eslint/no-misused-promises': 'warn',

            // General
            'no-console': ['warn', { allow: ['warn', 'error'] }],
        },
    },

    // ── Test files: relax some rules ──
    {
        files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
        rules: {
            '@typescript-eslint/no-explicit-any': 'off',
        },
    },

    // ── JavaScript files: disable type-aware rules, enable Node globals ──
    {
        files: ['**/*.js', '**/*.mjs', '**/*.cjs'],
        ...tseslint.configs.disableTypeChecked,
        languageOptions: {
            globals: {
                require: 'readonly',
                module: 'readonly',
                __dirname: 'readonly',
                __filename: 'readonly',
                process: 'readonly',
                console: 'readonly',
                Buffer: 'readonly',
                setTimeout: 'readonly',
                clearTimeout: 'readonly',
                setInterval: 'readonly',
                clearInterval: 'readonly',
            },
        },
        rules: {
            'no-undef': 'off',
            '@typescript-eslint/no-require-imports': 'off',
        },
    },

    // ── Prettier (must be last) ──
    prettierConfig,
];
