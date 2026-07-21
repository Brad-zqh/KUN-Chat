# KUN Chat

KUN Chat is a fan-made AI character chat interface built from public-expression
style notes and an explicitly approved local RAG corpus. It is not affiliated
with, endorsed by, or operated by Cai Xukun or his studio.

The repository contains the application code only. It does **not** contain API
keys, a cloned real-person voice, voice-training samples, private chat data, or
the local production RAG database.

## Features

- Responsive blue-themed web chat for desktop and mobile
- DeepSeek or MiniMax text generation
- Dual RAG: reviewed fact chunks for what to say plus short spoken examples for how to say it
- Fail-closed exclusion of unreviewed RAG candidates
- Browser recording plus mobile system-recorder fallback
- Local Whisper speech recognition
- Optional MiniMax/VoxCPM TTS integrations
- Optional MiniMax Music 3.0 original a-cappella lab (text-to-music only)
- Clear AI-character disclosure in the interface

## Local setup

Requirements: Python 3.11–3.14.

```powershell
Copy-Item .env.example .env.local
# Fill only your own provider credentials in .env.local.
uv sync
uv run python -m worker.web_server
```

Open <http://127.0.0.1:8766/chat.html> on the computer. A phone on the same
trusted Wi-Fi can use `http://<computer-LAN-IP>:8766/chat.html`; on ordinary
HTTP the page uses the phone's system recorder because browsers reserve direct
`getUserMedia` access for secure HTTPS origins.

## RAG data boundary

The default production source is:

```text
<KUN_MATERIAL_DIR>/transcripts/approved_rag
```

The runtime rejects production source paths that are not named `approved_rag`.
Unreviewed segment exports and `candidate_queue.jsonl` are never production
inputs. The verified baseline is **105 sources / 117 fact chunks + 424 style
examples**. See [the production baseline](docs/kunkun/production-rag-baseline.md).

## Voice and identity boundary

Public media availability is not proof of permission to train on or clone a
real person's voice. This repository ships no cloned voice and no real-person
voice samples. Configure a TTS Voice ID only when you possess independently
verifiable authorization from the speaker or rights holder.

Current documentation marker: `training_permission=unverified`.

## Deployment

GitHub Pages can host only the static frontend. Chat, RAG, STT, and TTS require
a separately hosted backend with server-side environment variables. Never put
provider secrets into the browser bundle or GitHub Pages settings exposed to
client code.

## Automatic GitHub synchronization

On Windows, install the fail-closed five-minute sync task once:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-auto-sync.ps1
```

The task pulls fast-forward remote changes, stages only the documented code
paths, rejects credentials and runtime/media files, runs the unit tests, then
commits and pushes `main`. Conflicts or failed tests stop synchronization
without force-pushing. Logs are written to
`%LOCALAPPDATA%\KUN-Chat\github-sync.log`.

To remove it:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall-auto-sync.ps1
```

## Original a-cappella lab

Set `KUN_MUSIC_ENABLED=true` and keep the MiniMax API key on the server. The
browser calls `/music/generate`; it never receives the key. The endpoint only
uses `music-3.0` or `music-3.0-free` text-to-music generation and intentionally
rejects reference audio, cover models, cloned voice IDs, and unconfirmed
lyrics. Generated URLs are temporary and expire after roughly 24 hours.

## Tests

```powershell
uv run python -m unittest discover -s tests -v
```

## License

See [LICENSE](LICENSE) and [NOTICE](NOTICE).
