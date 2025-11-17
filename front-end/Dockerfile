FROM node:lts-alpine

# keep dependencies needed by chokidar/Vite's file watcher
RUN apk add --no-cache libc6-compat

WORKDIR /code

# install dependencies first for better layer caching
COPY package*.json ./
RUN npm install

# include the rest of the source so the container can also run without bind mounts
COPY . .

EXPOSE 5173
ENV HOST=0.0.0.0 \
    PORT=5173

# Install (or update) dependencies inside the mounted workspace, then start the dev server
CMD [ "sh", "-c", "npm install && npm run dev -- --host ${HOST} --port ${PORT}" ]
