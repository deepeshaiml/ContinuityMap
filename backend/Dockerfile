FROM python:3.12.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/continuitymap /app/continuitymap
COPY data /app/data
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "continuitymap.main:app", "--host", "0.0.0.0", "--port", "8000"]
