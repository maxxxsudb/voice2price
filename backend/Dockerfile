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

# Создаем директорию для скрипта инициализации
RUN mkdir -p /docker-entrypoint-init.d

# Копируем скрипт инициализации БД при старте
COPY init_db_entrypoint.sh /docker-entrypoint-init.d/init_db.sh
RUN chmod +x /docker-entrypoint-init.d/init_db.sh

# Открываем порт
EXPOSE 5000

# Запускаем скрипт инициализации, а затем сервер
ENTRYPOINT ["/docker-entrypoint-init.d/init_db.sh"]
CMD ["python", "server.py"]
