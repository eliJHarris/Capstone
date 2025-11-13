FROM node:lts-alpine

# keep dependencies needed by chokidar/Vite's file watcher
RUN apk add --no-cache libc6-compat

WORKDIR /code

# install dependencies first for better layer caching
COPY package*.json ./
RUN npm install

RUN npm install axios

# copy project files and folders to the current working directory (i.e. 'app' folder)
# include the rest of the source so the container can also run without bind mounts
COPY . .

EXPOSE 5173
ENV HOST=0.0.0.0 \
    PORT=5173

# You will have to run command using sudo or su
# docker build -t vuejs-cookbook/dockerize-vuejs-app .
# docker run -it -p 8080:8080 --rm --name dockerize-vuejs-app-1 vuejs-cookbook/dockerize-vuejs-app
# access running site at localhost:8080
# Install (or update) dependencies inside the mounted workspace, then start the dev server
CMD [ "sh", "-c", "npm install && npm run dev -- --host ${HOST} --port ${PORT}" ]
