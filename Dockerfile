FROM node:24-slim

WORKDIR /app

# Копируем package файлы
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходники
COPY . .

# Открываем порт
EXPOSE 3000

# Запускаем dev сервер
CMD ["npm", "run", "dev"]
