FROM node:lts-alpine

RUN apk add --no-cache libc6-compat

WORKDIR /code

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
