// frontend/jest.config.js

const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: [
    '**/__tests__/**/*.test.[jt]s?(x)',  // FIXED: Only .test.js or .test.jsx files
    '**/__tests__/**/*.spec.[jt]s?(x)',  // Also .spec.js or .spec.jsx
  ],
  collectCoverageFrom: [
    'components/**/*.{js,jsx}',
    'hooks/**/*.{js}',
    'utils/**/*.{js}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
}

module.exports = createJestConfig(customJestConfig)