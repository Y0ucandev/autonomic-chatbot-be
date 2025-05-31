# autonomic-chatbot-be

## Description

This repository contains the backend of an autonomous chatbot designed to provide psychological support through natural, empathetic conversation. The chatbot is accessible via a dedicated web application, offering users a safe and private space to talk.


Key features:
- Psychological support chatbot accessible through a web app
- Natural language understanding and dynamic response generation
- Modular backend architecture using Docker Compose
- Prepared for future integrations and scenario expansion


## Installation

1. Clone repository
```bash
git clone https://github.com/Y0ucandev/autonomic-chatbot-be.git
```
2. Navigate the folder
```bash
cd autonomic_chatbot_be
```
3. Create .env file according to .env_template

4. Run the application
```bash
docker-compose up --build
```
## Users API Endpoints

### `POST /users/register`


Registers a new user.

- **Request body** (JSON):
  ```json
  {
    "name": "User",
    "email": "user@example.com",
    "password": "securePassword123",
    "age": 30,
    "gender": "male"
  }

### `POST /users/refresh_token`

Refreshes the access token using the refresh token sent in the Authorization header.

- **Headers:**
  - `Authorization: Bearer <refresh_token>`

- **Response example** (JSON):
  ```json
  {
    "access_token": "newAccessTokenString",
    "token_type": "bearer"
  }

### ` POST /users/login`
Logs in a user.

- **Request body** (JSON):
  ```json
  {
    "email": "user@example.com",
    "password": "securePassword123"
  }

- **Response example** (JSON):
  ```json
  {
  "access_token": "eyJhb...",
  "token_type": "bearer",
  "status": "success"
  }

### `GET /users/me`

Retrieves information about the currently authenticated user.

- **Headers:**
  - `Authorization: Bearer <access_token>`

- **Response** (JSON):
  ```json
  {
    "name": "John Doe",
    "email": "john.doe@example.com"
  }


## Message API Endpoints

### `GET /message/history`

Retrieves message history for a specified user.

- **Query parameters:**
  - `user_id` (integer, required) — ID of the user whose messages are retrieved
  - `limit` (integer, optional, default: 20) — Number of messages to retrieve (min 1, max 100)
  - `offset_id` (integer, optional, default: 0) — Offset ID for pagination

- **Response example** (JSON):
  ```json
  {
    "messages": [
      {
        "id": 101,
        "user_id": 1,
        "content": "Hello!",
        "timestamp": "2025-05-31T10:20:30Z"
      },
      {
        "id": 102,
        "user_id": 1,
        "content": "How are you?",
        "timestamp": "2025-05-31T10:22:10Z"
      }
    ]
  }

## Analysis API Endpoints
### `POST /analysis/sentiment`

Analyzes and saves sentiment scores for a conversation.

- **Request body** (JSON):
  ```json
  {
    "conversation_id": "abc123",
    "user_id": 1,
    "messages": [
      "Hello, how are you?",
      "I'm good, thanks!",
      "What about you?",
      "...",
      "Goodbye!"
    ]
  }


### `GET /analysis/sentiment/{conversation_id}`

Retrieves sentiment analysis records for a specific conversation.

- **Path parameters:**
  - `conversation_id` (string) — ID of the conversation to fetch sentiment analysis for

- **Response example** (JSON):
  ```json
  [
    {
      "id": 42,
      "conversation_id": "abc123",
      "start_state": 0.75,
      "end_state": 0.60,
      "user_id": 1
    },
    {
      "id": 43,
      "conversation_id": "abc123",
      "start_state": 0.80,
      "end_state": 0.55,
      "user_id": 2
    }
  ]


## Frontend

The frontend for this project — a web interface for the chatbot — is available here:  
[autonomic-chatbot-fe](https://github.com/Y0ucandev/autonomic-chatbot-fe.git)

## Requirements

Before you begin, make sure you have the following installed on your machine:

- [Docker](https://www.docker.com/get-started) 
