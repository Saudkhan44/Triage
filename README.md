# ai-service-kit

## The problem
A bank's support inbox is read in arrival order, so urgent cases (like fraud)
wait behind trivial ones.

## What this service does
Reads one message and returns category, priority, a short summary and a
confidence number as JSON, in about a second. It does not reply to customers
or take actions.

## What "good" means
- Never miss an urgent case. If money may be leaving, go urgent.
- Priority follows impact and time pressure, not tone or keywords.
- If the AI fails or answers badly, return a safe flagged fallback
  (other / medium, fallback: true) so a human reviews it.
- Speed, cost and accuracy are measured, not guessed.

## The contract
5 categories, 4 priorities, tie-break rules and a safe fallback are written in
docs/taxonomy.md. The prompt, the data shapes and the test labels all follow it.

## The exam
data/eval/eval_set.csv holds 40 labelled messages, including tricky ones
(calm but serious, angry but trivial, injection attacks). It is a small exam
with one author's labels, so a wrong label is possible.

## Run it

The CLI uses Python's standard library and an OpenAI-compatible Chat
Completions API. Set the provider settings in PowerShell, then classify a
message:

```powershell
$env:TRIAGE_API_KEY = "your-api-key"
$env:TRIAGE_MODEL = "your-model-name"
python -m app.triage "I see a transfer I did not make."
```

For an OpenAI-compatible provider with a different endpoint, also set
`TRIAGE_BASE_URL` to its API base URL (for example, `http://localhost:11434/v1`
for a local Ollama server). `TRIAGE_API_KEY` is optional for local providers.
You can pipe a message instead of passing an argument:

```powershell
"I cannot log in to my account." | python -m app.triage
```

Run the labeled evaluation with `python -m app.triage --eval`. This makes
provider calls for every example and reports category accuracy, priority
accuracy, urgent recall, and fallback count; provider usage may incur cost.
Provider errors or invalid model output are retried once, then return the
human-review fallback defined in `docs/taxonomy.md`.

Run the offline unit tests with `python -m unittest discover -s tests`.
