module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/*.test.ts'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  collectCoverage: true,
  coverageReporters: ['text-summary', 'lcov'],
  coverageThreshold: {
    global: {
      branches: 55,   // pinned below current 56.66%
      functions: 90,  // pinned below current 94.11%
      lines: 78,      // pinned below current 79.2%
      statements: 75, // pinned below current 75.47%
    },
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.test.ts',
    '!src/**/__tests__/**',
  ],
  coverageDirectory: 'coverage',
};
