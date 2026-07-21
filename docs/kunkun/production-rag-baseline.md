# KUN production RAG baseline

Updated: 2026-07-22

## Active production artifacts

- SQLite database: `D:\OneDrive\LLMs\talk-to-fengge\data\kunkun-rag.sqlite3`
- Approved retrieval text/SRT: `D:\OneDrive\LLMs\kun-material\transcripts\approved_rag`
- Double-gated source manifest: `D:\OneDrive\LLMs\kun-material\training\rag_documents.jsonl`
- Double-gated short speech style export: `D:\OneDrive\LLMs\kun-material\training\style_examples.jsonl`
- Semantic review ledger: `D:\OneDrive\LLMs\kun-material\manifests\semantic_review.csv`
- Review acceleration report: `D:\OneDrive\LLMs\kun-material\reports\RAG_REVIEW_ACCELERATION.md`
- Coverage report: `D:\OneDrive\LLMs\kun-material\reports\COVERAGE.md`
- Prefilter report: `D:\OneDrive\LLMs\kun-material\reports\RAG_PREFILTER.md`
- Style RAG report: `D:\OneDrive\LLMs\kun-material\reports\STYLE_RAG_UPGRADE_20260722.md`

Verified production baseline: **105 sources / 117 fact chunks + 424 style
examples**. The approved
directory currently contains 111 files; six files do not yield eligible chunks
under the production chunking rules.

KUN conversations use both retrieval lanes on every turn: `context_for()`
provides reviewed factual context (what to say), while `style_context_for()`
provides four reviewed short spoken examples (how to say it). At least half of
the selected style examples come from live/social natural speech when available.

## Production inclusion policy

Only files beneath a directory named `approved_rag` may be indexed. The runtime
fails closed if `KUN_APPROVED_TRANSCRIPT_DIR` points elsewhere. The former
`KUN_RAG_INCLUDE_UNREVIEWED` switch is not supported.

Never index any of the following as production context:

- `raw_segments_unreviewed`
- `rag_documents_unreviewed`
- `D:\OneDrive\LLMs\kun-material\review\candidate_queue.jsonl`

The 1,160-item candidate queue is advisory only: 113 `high_confidence_review`,
999 `manual_review`, and 48 `reject_candidate`. Human approval and both the
speaker and semantic gates remain mandatory before an item can reach
`approved_rag`.

Final upgraded ledger summary: 596 speaker-target segments, 588 semantic
`own_speech`, and 0 pending. Eight strictly verified adjacent live-speech
segments were restored without lowering the 0.82 speaker-similarity or 0.12
margin gates. The verified production total is 105 sources / 117 fact chunks +
424 style examples.

## Identity and voice authorization boundary

`training_permission=unverified`

Public availability of media is not proof of permission to train on or clone a
real person's identity or voice. Keep the AI-character disclosure visible and
retain a separate, verifiable authorization record before enabling real-person
voice cloning or distributing a cloned voice.

## Smoke test

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -c "from worker.rag_store import status; import json; print(json.dumps(status(), ensure_ascii=False, indent=2))"
.\.venv\Scripts\python.exe -m worker.rag_store --query "音乐 舞台 创作"
```

Expected status includes `source_policy=approved_only`,
`training_permission=unverified`, and the `105/117 facts + 424 style` production
baseline.
