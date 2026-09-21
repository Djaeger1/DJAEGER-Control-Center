FROM node:20-alpine
WORKDIR /app
COPY package.json server.js selftest.js isolation-check.js ./
COPY updates ./updates
RUN npm test
ENV NODE_ENV=production
EXPOSE 8080
CMD ["node","server.js"]
