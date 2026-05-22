module.exports = {
    testMatch: [
        '**/__tests__/**/*.test.js',
        '**/?(*.)+(spec|test).js'
    ],
    testPathIgnorePatterns: [
        '/node_modules/',
        '\\.d\\.ts$'
    ],
    collectCoverage: true,
    coverageReporters: ['text-summary', 'lcov'],
    // Pinned slightly below current baseline. Raise by ~2 points per quarter
    // OR whenever a patch organically improves coverage. See CONTRIBUTING.md.
    coverageThreshold: {
        global: {
            branches: 22,
            functions: 21,
            lines: 30,
            statements: 29,
        },
    },
    collectCoverageFrom: [
        'lib/**/*.js',
        '!lib/**/*.d.ts',
        '!lib/**/__tests__/**',
        '!lib/**/node_modules/**'
    ]
};
