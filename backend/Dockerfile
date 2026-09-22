# ============================
# Backend: Python + ffmpeg
# ============================
FROM python:3.11-slim

# Устанавливаем ffmpeg для конвертации аудио
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код (будет перезатерчен volume при запуске)
COPY . .

# Принудительно удаляем кэш Python и старые .pyc файлы, чтобы избежать конфликтов версий
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find /app -name "*.pyc" -delete 2>/dev/null || true

# Открываем порт
EXPOSE 5000

# Запускаем сервер
CMD ["python", "server.py"]
