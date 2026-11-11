import argparse
import csv
import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


CATEGORIES = {
    "fraud_or_unauthorized",
    "billing_or_fees",
    "account_access",
    "dispute_or_error",
    "other",
}
PRIORITIES = {"low", "medium", "high", "urgent"}
REQUIRED_FIELDS = {"category", "priority", "summary", "confidence", "fallback"}
FALLBACK_RESULT = {
    "category": "other",
    "priority": "medium",
    "summary": "",
    "confidence": 0.0,
    "fallback": True,
}
DEFAULT_BASE_URL = "https://api.openai.com/v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "triage_v2.md"
EVAL_PATH = Path(__file__).parent.parent / "data" / "eval" / "eval_set.csv"


class ProviderError(Exception):
    pass


def validate_result(content):
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("response is not valid JSON") from exc

    if not isinstance(result, dict) or set(result) != REQUIRED_FIELDS:
        raise ValueError("response does not have exactly the required fields")
    if result["category"] not in CATEGORIES:
        raise ValueError("response has an unknown category")
    if result["priority"] not in PRIORITIES:
        raise ValueError("response has an unknown priority")
    if not isinstance(result["summary"], str):
        raise ValueError("summary must be a string")
    if len(result["summary"]) > 200:
        raise ValueError("summary must be at most 200 characters")
    confidence = result["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("confidence must be a finite number from 0 to 1")
    if not isinstance(result["fallback"], bool):
        raise ValueError("fallback must be a boolean")
    return result


def request_completion(message, prompt, attempt):
    base_url = os.environ.get("TRIAGE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("TRIAGE_MODEL")
    if not model:
        raise ValueError("Set TRIAGE_MODEL to the model name for your provider.")

    system_prompt = prompt
    if attempt:
        system_prompt += (
            "\n\nYour previous response did not meet the output contract. "
            "Return one valid JSON object with exactly the five required fields. "
            "Do not include Markdown or any other text."
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("TRIAGE_API_KEY")
    if api_key:
        headers["Authorization"] = "Bearer " + api_key

    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = json.loads(response.read().decode("utf-8"))
        content = response_body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ProviderError("Provider returned a non-text response.")
        return content
    except urllib.error.HTTPError as exc:
        raise ProviderError(
            "Provider request failed with HTTP status {}.".format(exc.code)
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError("Could not reach the model provider.") from exc
    except (
        KeyError,
        IndexError,
        TypeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ProviderError("Provider returned an invalid response.") from exc


def classify(message):
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    last_error = None
    for attempt in range(2):
        try:
            return validate_result(request_completion(message, prompt, attempt))
        except (ProviderError, ValueError) as exc:
            last_error = exc
    print(
        "Warning: triage failed after one retry; returning the human-review fallback. "
        + str(last_error),
        file=sys.stderr,
    )
    return FALLBACK_RESULT.copy()


def evaluate():
    total = 0
    category_correct = 0
    priority_correct = 0
    urgent_total = 0
    urgent_found = 0
    fallback_count = 0

    with EVAL_PATH.open(newline="", encoding="utf-8") as eval_file:
        for row in csv.DictReader(eval_file):
            result = classify(row["narrative"])
            total += 1
            category_correct += result["category"] == row["true_category"]
            priority_correct += result["priority"] == row["true_priority"]
            if row["true_priority"] == "urgent":
                urgent_total += 1
                urgent_found += result["priority"] == "urgent"
            fallback_count += result["fallback"]

    metrics = {
        "examples": total,
        "category_accuracy": category_correct / total if total else 0,
        "priority_accuracy": priority_correct / total if total else 0,
        "urgent_recall": urgent_found / urgent_total if urgent_total else None,
        "fallbacks": fallback_count,
    }
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Classify one bank support ticket or evaluate the prompt."
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="classify every labeled example (makes one or more provider calls per row)",
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="customer message; if omitted, read it from standard input",
    )
    args = parser.parse_args()

    if args.eval and args.message is not None:
        parser.error("provide either --eval or a message, not both")
    if args.eval:
        evaluate()
        return

    message = args.message
    if message is None and not sys.stdin.isatty():
        message = sys.stdin.read()
    if not message or not message.strip():
        parser.error("provide a non-empty message or pipe one through standard input")

    print(json.dumps(classify(message), ensure_ascii=False))


if __name__ == "__main__":
    main()
