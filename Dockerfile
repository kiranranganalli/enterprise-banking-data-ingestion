FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home appuser

COPY --chown=appuser:appuser . .

RUN mkdir -p \
    data/state \
    data/output \
    data/rejected \
    data/benchmark \
    && chown -R appuser:appuser /app

USER appuser

CMD ["python", "main.py"]
