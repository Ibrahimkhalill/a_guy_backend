# Django FSM Chatbot

This Django project implements a **chat application** with a **Finite State Machine (FSM) chatbot**. Users can create chat rooms, send messages, and interact with a structured dialogue system. The chatbot can generate **SVG diagrams** and track user progress per chat room.

---

## Features

- Create and manage chat rooms
- Send and receive messages
- FSM-based chatbot for exercises and guided dialogue
- SVG diagram generation per message
- Persistent user FSM states
- File attachments for messages
- REST API with authentication

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Ibrahimkhalill/a_guy_backend.git
cd a_guy_backend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Apply migrations:

```bash
python manage.py migrate
```

5. Create a superuser (optional):

```bash
python manage.py createsuperuser
```

6. Run the server:

```bash
python manage.py runserver
```

---

## Configuration

- **Media files:** Ensure `MEDIA_ROOT` and `MEDIA_URL` are set in `settings.py`.

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

- **Parsed exercises JSON:** Place in `parsed_outputs/exercises_schema_v2_2025-09-22.json`.
- **SVG output directory:** Automatically created at `svg_outputs/`.
- **Pinecone index:** Configure in `chatbot.py` if needed.

---

## Usage

### Authentication

All endpoints require authentication (`IsAuthenticated`). Use Django REST Framework token authentication or session login.

### Chat Rooms

- List/Create rooms: `GET /rooms/`, `POST /rooms/`
- Retrieve/Update/Delete: `GET /rooms/<uuid>/`, `PATCH /rooms/<uuid>/`, `DELETE /rooms/<uuid>/`

### Messages

- List/Create messages: `GET /messages/`, `POST /messages/`
- Retrieve single message: `GET /messages/<id>/`

### FSM Bot Interaction

- FSM state is stored per user per chat room.
- Bot messages can include SVG diagrams.
- FSM state is saved in `ChatRoom.fsm_state_json`.

---

## API Endpoints

| Endpoint                  | Method | Description                  |
| ------------------------- | ------ | ---------------------------- |
| `/rooms/`                 | GET    | List user chat rooms         |
| `/rooms/`                 | POST   | Create new chat room         |
| `/rooms/<uuid>/`          | GET    | Retrieve chat room           |
| `/rooms/<uuid>/`          | PATCH  | Update chat room             |
| `/rooms/<uuid>/`          | DELETE | Delete chat room             |
| `/rooms/<uuid>/messages/` | GET    | List messages in a chat room |
| `/messages/`              | GET    | List all messages            |
| `/messages/`              | POST   | Send a new message           |
| `/messages/<id>/`         | GET    | Retrieve single message      |

---

## Example Request

```json
POST /messages/
{
  "room": 1,
  "text": "Solve exercise 5",
  "urls": [
    { "file_url": "https://example.com/file1.png", "type": "image" }
  ],
  "lang": "en"
}
```

Response:

```json
{
  "messages": [
    {
      "id": 10,
      "room": 1,
      "sender": "bot",
      "text": "Here is your exercise solution...",
      "urls": [
        { "file_url": "/media/chat/uploads/diagram.svg", "type": "image" }
      ],
      "timestamp": "2025-10-09T12:00:00Z"
    }
  ]
}
```

---

## Models Overview

- **ChatRoom:** Stores chat rooms and FSM states.
- **Message:** Stores messages from users and bots.
- **UploadedFile:** Stores uploaded files (SVG, images, etc.).
- **MessageURL:** Links messages to files.

---

## Notes

- Ensure `parsed_outputs` JSON exists; otherwise, FSM will not initialize.
- Cached FSM objects are stored in memory per user/room (`_user_room_fsms`).
- SVG files are saved to `media/chat/uploads/`.

---

## License

MIT License
