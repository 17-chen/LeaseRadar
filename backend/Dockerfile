FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home appuser
COPY backend /app/backend
COPY frontend /app/frontend
RUN mkdir /app/private && chown appuser:appuser /app/private
ENV PYTHONPATH=/app/backend DATA_DIR=/app/private
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
