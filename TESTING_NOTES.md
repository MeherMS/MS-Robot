# Testing Documentation

## Quick Start

### Run All Tests

**Backend:**
```bash
cd backend
pytest tests/ -v
```

**Frontend:**
```bash
cd frontend
npm test
```

### Run Tests in Watch Mode

**Backend:**
```bash
cd backend
pytest tests/ -v --tb=short --maxfail=1
```

**Frontend:**
```bash
cd frontend
npm run test:watch
```

### Check Coverage

**Backend:**
```bash
cd backend
pytest tests/ --cov=modules --cov=main --cov-report=term-missing
```

**Frontend:**
```bash
cd frontend
npm run test:coverage
```

## Test Structure

### Backend (60 tests)
- `tests/test_classifier.py` - 10 unit tests
- `tests/test_retriever.py` - 13 unit tests  
- `tests/test_endpoints.py` - 19 integration tests
- `tests/test_e2e_chat_flow.py` - 18 E2E tests

### Frontend (39+ tests)
- `__tests__/utils/api.test.js` - 13 unit tests
- `__tests__/hooks/useChat.test.js` - 11 unit tests
- `__tests__/components/ChatContainer.test.jsx` - 10 integration tests
- `__tests__/e2e/chat-flow.test.jsx` - 5+ E2E tests

## Important Notes

### Backend
- Requires: pytest, pytest-asyncio, httpx
- Config: `conftest.py` (shared fixtures)
- Run: `pytest tests/ -v`

### Frontend
- Requires: jest, @testing-library/react, @testing-library/jest-dom
- Config: `jest.config.js`, `jest.setup.js`
- Run: `npm test`

## CI/CD Integration

To integrate with GitHub Actions, create `.github/workflows/test.yml`:

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pytest tests/ -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: 18
      - run: cd frontend && npm install
      - run: cd frontend && npm test -- --coverage
```

## Debugging Failed Tests

### Backend
```bash
# Run single test with output
pytest tests/test_classifier.py::TestClassifier::test_classifier_detects_personal_intent_with_hobby_keyword -v -s

# Run with full traceback
pytest tests/ -v --tb=long
```

### Frontend
```bash
# Run single test
npm test -- api.test.js

# Run in debug mode
node --inspect-brk node_modules/.bin/jest --runInBand
```

## Notes
- All tests must pass before merging to main
- Add tests for any new features/fixes
- Update TESTING_REPORT.md when adding major test suites
EOF

git add TESTING_NOTES.md
git commit -m "docs: add testing documentation and CI/CD guide"