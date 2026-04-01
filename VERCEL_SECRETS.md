Vercel Secrets & Environment Checklist

Required (frontend):
- `backend_url` (secret): public URL of the deployed backend API (e.g., https://api.example.com). Set `REACT_APP_API_BASE` to `@backend_url` in Vercel env.

Recommended (if you host backend elsewhere):
- `CHROMA_HOST`, `CHROMA_PORT` — only if your frontend needs to call Chroma directly (not recommended).

Backend-hosting note
- The backend contains heavy libs (TensorFlow, ChromaDB) and persistent storage; host it on a container-friendly platform and expose a secure HTTPS endpoint. Do not attempt to build the backend as Vercel Serverless functions.

Environment scoping
- Add secrets for `Production` and `Preview` scopes in the Vercel dashboard so PR previews can use preview endpoints.

How to add a secret via CLI
```bash
vercel env add BACKEND_URL production
# follow prompts and paste secret value
```
