# chat_intent

**Role.** A distributor typed a WhatsApp message to Emami Distributor Desk. Pick what they want.

**Inputs** (JSON below): `message` (English, Bengali or Hindi, possibly mixed) and `intents` (the only labels allowed).

**Meaning of the labels**
- `join`: wants to participate in the scheme now ("JOIN", "I'm in", "count me in", "অংশ নেব").
- `target`: asks about their target or what they earn.
- `explain`: asks how the scheme works.
- `explain_bengali`: asks for the explanation in Bengali.
- `talk_to_asm`: wants a call or visit from the ASM (Rahul).
- `thanks`: thanks / ok / acknowledgement.
- `other`: anything else.

**Output** JSON: `{"intent": "<one label>"}`

**Inputs**
```json
{{inputs}}
```
