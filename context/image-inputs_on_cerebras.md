# Image Inputs (Cerebras Chat Completions)

Source: https://inference-docs.cerebras.ai/capabilities/image-inputs

## Supported Models

Currently available with `qwen-3.8-27b` on the public shared tier, `gemma-4-31b` on
Dedicated Endpoints, and other image-capable models on Dedicated Endpoints.

Constraints (as of 2026-09-07): PNG and JPEG only, no external URLs (base64 data URIs
only), width and height each <= 15,000 px, 10 MiB total request payload, and 2 images
per request on the free trial / 10 on Developer tier. Images may only appear in `user`
messages.

## Request Format

Images are sent as base64-encoded data URIs inside the `messages` array's `content`
field, which becomes a list of content blocks instead of a plain string:

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What claims does this image make?"},
    {
      "type": "image_url",
      "image_url": {"url": "data:image/png;base64,<...>"}
    }
  ]
}
```

- Only `image/png` and `image/jpeg` are supported — no external image URLs.
- Multiple images can be included in one request: 2 max on the Free Trial tier,
  10 max on Developer/Enterprise shared tier (higher limits possible on Dedicated
  Endpoints or with explicit org configuration).

## Token Usage

Each image costs up to 280 tokens, based on how its dimensions are scaled/rounded
to multiples of 48px during preprocessing — file size does not directly affect
token cost.

## Limitations

Not reliable for: medical imaging, small/low-res text, rotated/upside-down
content, graphs distinguished only by color, precise spatial reasoning, CAPTCHAs.
Text embedded in an image becomes part of the model's prompt context alongside
user text, which is a prompt-injection consideration for untrusted image sources.
