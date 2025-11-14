FROM node:lts-alpine

# install SPA-friendly static server
RUN npm install -g serve

ENV VITE_AUTH_API_BASE_URL=https://localhost/auth

# make the 'app' folder the current working directory
WORKDIR /app

# copy both 'package.json' and 'package-lock.json' (if available)
COPY package*.json ./

# install project dependencies
RUN npm install

# copy project files and folders to the current working directory (i.e. 'app' folder)
COPY . .

# build app for production with minification
RUN npm run build

EXPOSE 8080
CMD [ "serve", "-s", "dist", "-l", "8080" ]

# You will have to run command using sudo or su
# docker build -t vuejs-cookbook/dockerize-vuejs-app .
# docker run -it -p 8080:8080 --rm --name dockerize-vuejs-app-1 vuejs-cookbook/dockerize-vuejs-app
# access running site at localhost:8080
