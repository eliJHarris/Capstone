FROM node:lts-alpine AS build

WORKDIR /app

<<<<<<< HEAD
=======
WORKDIR /code

# Install dependencies
>>>>>>> d10ffe2744ce689267853a09c3e3e358961e5b46
COPY package*.json ./
RUN npm ci

<<<<<<< HEAD
=======
#include the rest of the source so the container can also run without bind mounts
>>>>>>> d10ffe2744ce689267853a09c3e3e358961e5b46
COPY . .
RUN npm run build

FROM nginx:1.25-alpine AS runtime

<<<<<<< HEAD
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
=======
# Install (or update) dependencies inside the mounted workspace, then start the dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
>>>>>>> d10ffe2744ce689267853a09c3e3e358961e5b46
