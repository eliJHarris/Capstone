FROM node:lts-alpine

RUN apk add --no-cache libc6-compat

WORKDIR /code

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of your project
COPY . .

EXPOSE 5173
ENV HOST=0.0.0.0 \
    PORT=5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
