module.exports = {
    testMatch: [
        '**/__tests__/**/*.test.js',
        '**/?(*.)+(spec|test).js'
    ],
    testPathIgnorePatterns: [
        '/node_modules/',
        '\\.d\\.ts$'
    ],
    collectCoverageFrom: [
        'lib/**/*.js',
        '!lib/**/*.d.ts',
        '!lib/**/__tests__/**',
        '!lib/**/node_modules/**'
    ]
};
