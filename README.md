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