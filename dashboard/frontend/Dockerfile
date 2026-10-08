FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
EXPOSE 5173
ENTRYPOINT ["./entrypoint.sh"]
