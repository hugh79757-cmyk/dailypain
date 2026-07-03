export default [
    {
        ignores: ["node_modules/**", ".wrangler/**"],
    },
    {
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                Response: "readonly",
                Request: "readonly",
                URL: "readonly",
                crypto: "readonly",
            },
        },
        rules: {
            "no-unused-vars": "warn",
            "no-undef": "error",
            "semi": ["error", "always"],
            "quotes": ["warn", "double"],
            "no-trailing-spaces": "warn",
            "eol-last": ["error", "always"],
        },
    },
];
