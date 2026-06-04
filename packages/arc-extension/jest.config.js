module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testMatch: [
        '**/__tests__/**/*.test.[jt]s?(x)',
        '**/?(*.)+(spec|test).[jt]s?(x)'
    ],
    testPathIgnorePatterns: [
        '/node_modules/',
        '/lib/',
        '\\.d\\.ts$'
    ],
    collectCoverage: true,
    coverageReporters: ['text-summary', 'lcov'],
    // Pinned slightly below current baseline. Raise by ~2 points per quarter
    // OR whenever a patch organically improves coverage. See CONTRIBUTING.md.
    coverageThreshold: {
        global: {
            branches: 18,
            functions: 20,
            lines: 27,
            statements: 26,
        },
    },
    collectCoverageFrom: [
        'src/**/*.{ts,tsx}',
        '!src/**/*.d.ts',
        '!src/**/__tests__/**',
        '!src/**/node_modules/**'
    ],
    moduleNameMapper: {
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
    }
};
