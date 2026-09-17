import js from '@eslint/js'

export default [
    {
        ignores: ['node_modules/**', 'dist/**', 'legacy/**']
    },
    js.configs.recommended,
    {
        rules: {
            'no-unused-vars': 'off',
            'no-useless-assignment': 'off',
            'no-empty': 'off'
        },
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            globals: {
                window: 'readonly', document: 'readonly', navigator: 'readonly',
                console: 'readonly', setTimeout: 'readonly', setInterval: 'readonly',
                clearTimeout: 'readonly', clearInterval: 'readonly', FormData: 'readonly',
                FileReader: 'readonly', location: 'readonly', history: 'readonly',
                localStorage: 'readonly', sessionStorage: 'readonly', fetch: 'readonly', Event: 'readonly',
                URL: 'readonly', Blob: 'readonly', alert: 'readonly', URLSearchParams: 'readonly'
            }
        }
    }
]
