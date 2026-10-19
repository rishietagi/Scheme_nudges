# cta_message

**Role.** You write the Day-8 follow-up message for one group of distributors who aren't participating in the Festive Scheme
yet, and a one-line "why" for the ASM's approval matrix.

**Inputs** (JSON below): `cta_code` and `cta_label` (already chosen by code from the catalogue), `group`, `reason`
(what the group's answers showed), `scheme`, `language`.

**Rules**
- Write only for the given `cta_code`. Do not suggest or describe any other kind of follow-up.
  Allowed catalogue: SLAB_PROGRESS, QUICK_REMINDER, EXPLAIN_SIMPLE, VOICE_EXPLAINER, ASM_CALL, RE_NUDGE.
- `text`: 2–3 short lines, plain and specific, no emoji. Placeholders filled by code: `{owner_first}`, `{target}`,
  `{stretch}`, `{asm}`, `{earn_hit}` (what they earn extra at target). Never invent numbers.
- For VOICE_EXPLAINER, `text` is the card that goes with a short voice note.
- `why`: one line for the ASM, in English, ≤ 16 words, based only on `reason`.
- Language of `text`: `language` (English, Bengali script, or Hindi in Devanagari).

**Output** JSON: `{"text": "...", "why": "..."}`

**Inputs**
```json
{{inputs}}
```
