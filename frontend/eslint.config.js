import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import simpleImportSort from 'eslint-plugin-simple-import-sort'
import tseslint from 'typescript-eslint'
import js from '@eslint/js'
import stylistic from '@stylistic/eslint-plugin'

export default tseslint.config(
    // components/ui i use-mobile pochodzą w całości z generatora shadcn.
    { ignores: ['dist', 'components/ui', 'hooks/use-mobile.ts'] },
    js.configs.recommended,
    {
        files: ['**/*.{ts,tsx}'],
        extends: [tseslint.configs.strictTypeChecked],
        languageOptions: {
            ecmaVersion: 15,
            parserOptions: {
                projectService: true,
                tsconfigRootDir: import.meta.dirname,
            },
        },
        plugins: {
            'react-hooks': reactHooks,
            'react-refresh': reactRefresh,
        },
        rules: {
            ...reactHooks.configs.recommended.rules,
            'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
            '@typescript-eslint/prefer-nullish-coalescing': 'off',
            '@typescript-eslint/consistent-type-definitions': ['error', 'type'],
            '@typescript-eslint/no-unnecessary-template-expression': 'off',
            '@typescript-eslint/no-confusing-void-expression': 'off',
            '@typescript-eslint/no-misused-promises': 'warn',
            '@typescript-eslint/restrict-template-expressions': 'off',
            '@typescript-eslint/no-unnecessary-condition': 'off',
            '@typescript-eslint/unbound-method': 'off',
            '@typescript-eslint/prefer-reduce-type-parameter': 'off',
        },
    },
    {
        // Rozszerzanie globalnych typów (np. ImportMetaEnv) wymaga declaration merging,
        // które działa tylko na interfejsach.
        files: ['**/*.d.ts'],
        rules: {
            '@typescript-eslint/consistent-type-definitions': 'off',
        },
    },
    {
        plugins: {
            '@stylistic': stylistic,
        },
        rules: {
            ...stylistic.configs.customize({
                indent: 4,
                commaDangle: 'always-multiline',
                blockSpacing: true,
                arrowParens: true,
            }).rules,
            '@stylistic/no-extra-semi': 'off',
            '@stylistic/semi': 'off',
            '@stylistic/member-delimiter-style': [
                'error',
                {
                    multiline: {
                        delimiter: 'semi',
                        requireLast: true,
                    },
                    singleline: {
                        delimiter: 'semi',
                        requireLast: false,
                    },
                    multilineDetection: 'brackets',
                },
            ],
            '@stylistic/no-multiple-empty-lines': [
                'error',
                {
                    max: 2,
                    maxEOF: 1,
                },
            ],
            '@stylistic/eol-last': ['error', 'always'],
            '@stylistic/jsx-indent-props': ['error', 4],
            '@stylistic/operator-linebreak': [
                'error',
                'before',
                {
                    overrides: {
                        '=': 'after',
                    },
                },
            ],
        },
    },
    {
        plugins: {
            'simple-import-sort': simpleImportSort,
        },
        rules: {
            'simple-import-sort/imports': [
                'error',
                {
                    groups: [['^react$', '^[a-z]', '^@\\w+'], ['^@/'], ['^\\.\\.(?!/?$)', '^\\.\\./?$', '^\\./(?=.*/)(?!/?$)', '^\\.(?!/?$)', '^\\./?$'], ['"^.+\\\\.types?"'], ['^.+\\.png', '^.+\\.jpe?g', '^.+\\.svg']],
                },
            ],
        },
    },
)
