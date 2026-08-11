# Gemma 4 31B (on Cerebras)

Source: https://inference-docs.cerebras.ai/models/gemma-4-31b

Multimodal model (text + image input, text output) hosted on Cerebras, optimized for
visual reasoning as well as general chat/reasoning tasks.

## Model Stats

- **Model ID:** `gemma-4-31b`
- **Context window:** 65k tokens (Free Trial) / 131k tokens (Paid tiers)
- **Max throughput:** ~1,850 tokens/sec
- **Input formats:** text, image (base64 PNG/JPEG only — no external image URLs)
- **Output formats:** text

## Pricing (per million tokens)

- Input: $0.99
- Output: $1.49

## Rate Limits

| Tier | Requests/min | Input tokens/min | Daily tokens | Images/request |
|---|---|---|---|---|
| Free Trial | 5 | 30k | 1M | 2 |
| Developer/Paid | 300 | 500k | N/A | 10 |

## Capabilities

Image Inputs, Reasoning, Streaming, Sampling Controls, Structured Outputs, Tool
Calling, Parallel Tool Calling, Prompt Caching.

## Known Limitations

- Cannot reliably handle medical imaging (CT/MRI), small/low-res text, rotated or
  upside-down content, graphs distinguished only by color, precise spatial
  reasoning, or CAPTCHAs.
- Text embedded in an image is included in the model's prompt context alongside
  user text — treat image sources the same as any other untrusted input
  (prompt-injection risk if the image comes from an untrusted party).
- Image inputs are only available on the Chat Completions endpoint (not
  Completions), and not on all Dedicated Endpoint deployments.
