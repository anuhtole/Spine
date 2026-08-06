FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY spine /app/spine
COPY tools /app/tools
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

EXPOSE 8000

CMD ["uvicorn", "spine.main:app", "--host", "0.0.0.0", "--port", "8000"]
