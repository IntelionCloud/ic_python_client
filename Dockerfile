FROM python:3.12-slim

WORKDIR /app

# Install package with dev dependencies
COPY pyproject.toml README.md ./
COPY intelion_cloud/ intelion_cloud/
RUN pip install --no-cache-dir -e ".[dev]"

# Copy tests
COPY tests/ tests/

CMD ["pytest", "tests/", "-v", "--tb=short"]
