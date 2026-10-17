FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    PYTHONUNBUFFERED=1

RUN useradd --no-create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["python", "-m", "src.server"]
