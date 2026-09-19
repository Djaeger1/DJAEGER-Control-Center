FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY server.js ./
COPY selftest.js ./
ENV NODE_ENV=production
RUN npm test
EXPOSE 3000
CMD ["node","server.js"]
