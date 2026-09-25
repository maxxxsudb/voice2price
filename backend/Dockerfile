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

# Копируем код
COPY . .

# Копируем скрипт инициализации БД при старте (в /app, чтобы не зависеть от CRLF)
COPY init_db_entrypoint.sh /app/init_db_entrypoint.sh
RUN sed -i 's/\r$//' /app/init_db_entrypoint.sh && chmod +x /app/init_db_entrypoint.sh

# Открываем порт
EXPOSE 5000

# Запускаем скрипт инициализации, а затем сервер
ENTRYPOINT ["/bin/bash", "/app/init_db_entrypoint.sh"]
CMD ["python", "server.py"]
