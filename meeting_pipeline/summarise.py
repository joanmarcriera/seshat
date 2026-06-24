"""Build the meeting-notes prompt and call Ollama."""

from __future__ import annotations

from typing import Any, Callable

import requests


class SummariseError(Exception):
    pass


# NOTE: copied verbatim from summarise-transcript-ollama.sh (the prompt body).
# Keep the two scripts in sync if either changes.
PROMPT_TEMPLATE = """You are analysing a cleaned meeting transcript.

Your job is to produce concise, structured professional meeting notes and a clear post-meeting ROI plan.

The transcript has speaker labels but no timestamp ranges. This is intentional. Do not ask for timestamps and do not reproduce timestamp ranges.

The notes are for: {note_owner}.
Known speaker label for the note owner: {user_speaker}.

Important rules:
- Do not invent facts.
- Preserve uncertainty.
- If something is unclear, write "unclear".
- Separate explicit statements from reasonable inferences.
- Extract action items only where there is evidence in the transcript.
- Identify likely transcription errors where useful.
- Use British English.
- The output must be practical and decision-oriented.
- Keep the whole answer concise and avoid repeated wording.
- Do not copy long transcript passages. Evidence should be short speaker-specific excerpts.
- If no useful evidence exists for a section, write "unclear" or "none stated".
- The "Highest-ROI follow-up" and "30-minute post-meeting plan" sections must advise the note owner, not the other party.
- If the note owner's speaker label is unknown, infer cautiously from the meeting purpose and phrase advice as "For the note owner".
- Do not create internal debrief steps for the other party unless the note owner is clearly responsible for them.

Important anti-hallucination rules:
- Do not assign real names to SPEAKER_00 or SPEAKER_01 unless the transcript explicitly identifies them.
- If a person is mentioned by name, do not assume they are one of the speakers.
- Do not add calendar years unless explicitly stated in the transcript.
- For action items, distinguish:
  1. Explicit action items
  2. Implied next steps
  3. Possible future responsibilities
- If an action depends on hiring/onboarding, mark the deadline as "Post-engagement / not yet active".
- If a company/entity relationship is unclear, write "unclear" rather than resolving it.

Return the output in Markdown using exactly these sections:

# Meeting notes

## Executive summary

## Context

## Key people and organisations

## Opportunity or purpose

## Technical scope

## Role expectations

## Commercial and compensation discussion

## Timeline

## Decisions made

## Action items

Use this table:

| Action | Owner | Deadline | Evidence | Confidence |
|---|---|---|---|---|

## Highest-ROI follow-up

Rank the 3-5 follow-up moves most likely to convert the meeting into value. Optimise for clarity, commitment, money/career upside, leverage, or reduced risk. Avoid generic busywork.

Use this table:

| Priority | Next move | Why it matters | Timebox | Evidence | Confidence |
|---|---|---|---|---|---|

## 30-minute post-meeting plan

## Open questions for next call

## Risks and concerns

## Possible transcription corrections

## Suggested follow-up email

Write the suggested email in a professional but natural tone. Do not make it too long.

Transcript:

{transcript_text}
"""


def build_prompt(transcript_text: str, note_owner: str, user_speaker: str) -> str:
    return PROMPT_TEMPLATE.format(
        note_owner=note_owner,
        user_speaker=user_speaker,
        transcript_text=transcript_text,
    )


def ollama_reachable(
    url: str,
    *,
    timeout: int = 4,
    get: Callable[..., Any] | None = None,
) -> bool:
    get = get or requests.get
    try:
        response = get(url.rstrip("/") + "/api/tags", timeout=timeout)
        return getattr(response, "status_code", 500) == 200
    except Exception:
        return False


def summarise(
    transcript_text: str,
    *,
    url: str,
    model: str,
    options: dict[str, Any],
    note_owner: str,
    user_speaker: str,
    timeout: int = 3600,
    post: Callable[..., Any] | None = None,
) -> tuple[str, dict]:
    post = post or requests.post
    prompt = build_prompt(transcript_text, note_owner, user_speaker)
    try:
        response = post(
            url.rstrip("/") + "/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": options},
            timeout=timeout,
        )
        response.raise_for_status()
        raw = response.json()
    except Exception as exc:
        raise SummariseError(f"Ollama request failed: {exc}") from exc
    text = (raw.get("response") or "").strip()
    if not text:
        raise SummariseError("Ollama returned an empty response.")
    return text, raw
