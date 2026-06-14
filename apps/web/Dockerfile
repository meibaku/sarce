FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

COPY apps/web apps/web

EXPOSE 3000

CMD ["npm", "run", "dev", "--workspace=apps/web", "--", "--hostname", "0.0.0.0"]
