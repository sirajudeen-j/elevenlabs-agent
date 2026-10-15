# NovaMart — voice-assisted online store

A demo storefront with a FastAPI backend, a React + Vite frontend, and **Nova**,
an ElevenLabs voice agent that can look up orders, verify customers, and change
shipping addresses by voice.

```
novamart/
├── backend/                  # FastAPI + SQLite/Turso
│   ├── main.py               # all API endpoints + catalog + identity store
│   ├── database.py           # SQLite locally, Turso (libSQL over HTTP) deployed
│   ├── tests/test_api.py     # pytest API suite
│   └── .env.example
├── frontend/                 # React + Vite
│   └── src/
│       ├── components/VoiceAgent.jsx   # "Talk to Nova" — WebRTC voice UI
│       ├── context/CartContext.jsx     # shared cart state
│       └── pages/            # Home, Products, Cart, Checkout, OrderConfirmation, Orders
└── docs/
    └── elevenlabs-agent-setup.md       # Nova: prompt, workflow, tool JSON, tests
```

## API surface

| Method | Path | Used by | Purpose |
|---|---|---|---|
| `GET` | `/api/products` | Storefront | Product catalog (8 SKUs, 2 categories) |
| `GET` | `/api/orders` | Storefront | All orders |
| `POST` | `/api/create_order` | Storefront | Create order — generated ID, delivery **+3 days**, status `processing` |
| `POST` | `/api/lookup_order` | Voice agent | Order by ID; 200 + `{"status":"not_found"}` when missing |
| `POST` | `/api/verify_identity` | Voice agent | Account number + postcode check (KBA) |
| `POST` | `/api/update_shipping_address` | Voice agent | Address change — **owner-only** (see Security) |

The full schema is in `openapi.yaml` (repo root).

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload          # http://localhost:8000
```

With zero configuration the backend uses a local SQLite file
(`backend/novamart.db`) and seeds two demo orders (`ORD-1001`, `ORD-1002`).
API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env               # then fill in VITE_ELEVENLABS_AGENT_ID
npm run dev                        # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `localhost:8000`, so no CORS setup is
needed in development.

### 3. ElevenLabs agent

Follow `docs/elevenlabs-agent-setup.md`. In short:

1. Create the agent in the ElevenLabs dashboard (single agent + the small
   verification workflow from the doc).
2. Add the three webhook tools with the URLs from §5 of that doc
   (`/api/lookup_order`, `/api/verify_identity`,
   `/api/update_shipping_address`). For local development expose the backend
   with `ngrok http 8000` and use the https URL.
3. Copy the agent ID into `frontend/.env` as `VITE_ELEVENLABS_AGENT_ID`.
4. Reload the frontend and click **Talk to Nova** (bottom-right). The browser
   will ask for microphone access; the panel shows a live transcript and
   whether Nova is listening or speaking.

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Purpose |
|---|---|---|
| `SQLITE_PATH` | No (default `./novamart.db`) | Location of the local SQLite file |
| `TURSO_DATABASE_URL` | Deployed | Turso DB URL (`libsql://...` or `https://...`) |
| `TURSO_AUTH_TOKEN` | Deployed | Turso auth token |

If both Turso variables are set, `database.py` talks to Turso over HTTP
(Hrana `/v2/pipeline`); otherwise it falls back to local SQLite. Check which
backend is active at `GET /api/health`.

### Frontend (`frontend/.env`)

| Variable | Required | Purpose |
|---|---|---|
| `VITE_API_URL` | No in dev | Backend base URL; unset → Vite proxy is used |
| `VITE_ELEVENLABS_AGENT_ID` | Yes for voice | The ElevenLabs agent ID (`agent_...`) |

## Running the tests

```bash
cd backend
python -m pytest tests/ -v
```

15 tests cover: the store API (catalog, order creation incl. ID sequence,
3-day delivery date, `processing` status), the voice tools (lookup found /
not-found, identity success / rejection, address update happy path), and the
regressions fixed in this sprint:

- **unknown product IDs** in `create_order` are now rejected with HTTP 400
  and the offending IDs (they used to be silently skipped),
- **address changes are owner-only** — a mismatched `account_number` gets
  HTTP 403 and the order is untouched,
- **no `datetime.utcnow()`** anywhere — an AST-based test fails the suite if
  the deprecated call comes back.

## Security

`update_shipping_address` is the privileged operation. Two layers of defense:

1. **Agent side** — the ElevenLabs workflow only exposes the tool after
   `verify_identity` returns `success` in the current conversation, and the
   `account_number` sent is the verified one from agent state, not free text
   (see `docs/elevenlabs-agent-setup.md` §2/§5).
2. **Backend side** — the endpoint checks that `account_number` matches the
   account that owns the order. Mismatch → `403 {"error": "forbidden"}`.
   Orders placed as guest (no account number) cannot be modified over the
   voice channel at all.

The previous implementation accepted `account_number` but never checked it;
the fix and its tests are in `main.py` and `tests/test_api.py`
(`test_update_shipping_address_rejects_non_owner`).

## Demo script

1. `GET /api/products` → add items to cart → checkout with account number
   `10000001` → land on the confirmation page with the new `ORD-####` ID.
2. Open **Order Tracker** in the navbar → enter the ID → status stepper.
3. Click **Talk to Nova** → "Where is my order ORD-1001?" → Nova calls
   `lookup_order` and reads status + delivery date.
4. "Change my shipping address" → Nova asks for account number (`10000001`)
   and postcode (`94107`) → `verify_identity` succeeds → confirm the new
   address → `update_shipping_address` → the change is visible immediately
   in the Order Tracker.
5. Wrong postcode three times → Nova locks out and offers a human.

| Account number | Postcode | Customer | Orders | Use for |
|---|---|---|---|---|
| `10000001` | `94107` | Jordan Rivera | `ORD-1001` (shipped) | Happy path |
| `10000002` | `10001` | Sam Patel | `ORD-1002` (processing) | Second account |
| anything else | — | — | — | Retry / lockout path |
