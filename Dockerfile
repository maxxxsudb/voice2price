# ============================
# Frontend: Node 24 slim
# ============================
FROM node:24-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем package-файлы отдельно для кэширования слоёв
COPY package.json package-lock.json* ./

# Устанавливаем зависимости
RUN npm ci --ignore-scripts

# Копируем исходники (будут перезатерчены volume при запуске)
COPY . .

# Открываем порт
EXPOSE 3000

# Переменная окружения — URL бэкенда
# В docker-compose пробрасывается через .env
ENV VITE_BACKEND_URL=http://localhost:5000

# Запускаем dev-сервер
CMD ["npm", "run", "dev"]
