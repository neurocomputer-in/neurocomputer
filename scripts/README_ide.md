# neuro IDE — quickstart

## run both sides

```bash
# Terminal 1 — IDE backend (port 8000)
python3 scripts/ide_server.py

# Terminal 2 — neuro_web dev (port 3000, already in use? see below)
cd neuro_web
NEXT_PUBLIC_IDE_URL=http://127.0.0.1:8000 npm run dev

# Open
open http://localhost:3000/graph
```

## what u get

- every neuro in the library, grouped by kind namespace (skill, prompt,
  memory, model, agent, context, instruction, code)
- live search (name, description, category, kind)
- click a neuro → drawer w/ full details:
  - typed inputs / outputs
  - uses + children (clickable — drills into each)
  - raw `conf.json` source
  - raw `code.py` source
  - raw `prompt.txt` (if present)
- colour-coded per namespace for visual scan

## swapping the backend port

```bash
python3 scripts/ide_server.py --port 9000
# then
NEXT_PUBLIC_IDE_URL=http://127.0.0.1:9000 npm run dev
```

## api (separate from server.py on port 7000 — untouched)

| endpoint                       | method | returns                        |
|--------------------------------|--------|--------------------------------|
| `/api/health`                  | GET    | `{ok, neuros}`                |
| `/api/neuros`                  | GET    | list w/ full describe() shape  |
| `/api/neuros/{name}`           | GET    | describe + conf/code/prompt src|
| `/api/kinds`                   | GET    | `{namespace: [names]}`         |
| `/api/categories`              | GET    | `{category: [names]}`          |
| `/api/snapshots/{name}`        | GET    | list of snapshot timestamps    |
| `/api/neuros/validate`         | POST   | dev_pipeline validate op       |
| `/api/neuros/save`             | POST   | dev_pipeline save op           |
| `/api/neuros/{name}/rollback`  | POST   | dev_pipeline rollback          |

The write endpoints all funnel through `dev_pipeline` → safe-save
(schema gate + syntax gate + snapshot + atomic rename). Writes default
to `author=ai` — which enforces the forbidden-call scan. Pass
`{"author":"human"}` in the body to bypass when editing by hand.

## next iterations

- live WebSocket for hot-reload updates → frontend refreshes automatically
- visual graph layout (react-flow or three-fiber) showing uses edges
- inline edit w/ monaco + validate/save buttons
- "AI, modify this neuro" chat panel wired to dev_pipeline
