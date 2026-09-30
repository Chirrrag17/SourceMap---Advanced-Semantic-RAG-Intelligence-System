FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY codebase_context ./codebase_context
COPY sourcemap ./sourcemap
RUN pip install --no-cache-dir '.[api]'
EXPOSE 8000
CMD ["uvicorn", "sourcemap.api:app", "--host", "0.0.0.0", "--port", "8000"]
