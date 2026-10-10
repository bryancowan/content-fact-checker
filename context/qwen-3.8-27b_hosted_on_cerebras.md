# Qwen 3.8 27B (hosted on Cerebras)

Source: https://inference-docs.cerebras.ai/models/qwen-3.8-27b
Retrieved: 2026-09-07

**Model ID:** `qwen-3.8-27b`

Replaced `gemma-4-31b` in this app on 2026-09-07. Cerebras retired `gemma-4-31b`
on 2026-09-03 and names `qwen-3.8-27b` as its recommended replacement
(https://inference-docs.cerebras.ai/support/deprecation).

## Limits

| | Free Trial | Paid (Developer) |
|---|---|---|
| Context window | 64K | 128K |
| Max output tokens | 32K | 40K |
| Requests/min | 5 | 300 |
| Tokens/min (uncached) | 30K | 150K |
| Tokens/min (total) | 90K | 750K |
| Tokens/day | 1M | no daily cap |
| Images per request | 2 | 10 |

Developer-tier total tokens/min was raised from 450K to 750K on 2026-09-22
(https://inference-docs.cerebras.ai/support/change-log). The uncached limit is
unchanged at 150K. The other figures above are as retrieved 2026-09-07.

Throughput ~1500 tokens/second. Pricing: $0.99 / M input tokens,
$1.49 / M output tokens.

## Capabilities

- Tool calling, including parallel tool calling
- Structured outputs with `strict: true` (constrained decoding), on the public
  shared tier
- Streaming
- Sampling controls
- Vision (see `image-inputs_on_cerebras.md`)

## Reasoning

**Reasoning is enabled by default at `high`.** This is the key difference from
`gemma-4-31b`, which defaulted to `none`.

- `reasoning_effort`: `none` | `low` | `medium` | `high` (default `high`).
  The model page lists only `high`/`none`, but the reasoning capability page and
  the Python SDK's type signature both accept all four.
- `reasoning_format`: `parsed` | `raw` | `hidden` | `none`. With `parsed`,
  reasoning is returned in `choices[0].message.reasoning` and `message.content`
  holds only the final answer. This app pins `parsed` so structured-output JSON
  parsing keeps working.

**Reasoning tokens count toward `max_completion_tokens`** and the reported
completion-token usage. Budget for them: too small a budget yields truncated or
empty content.

## Parameter notes

- `max_tokens` is deprecated in favor of `max_completion_tokens`. Do not send both.
- The Python SDK (`cerebras_cloud_sdk`) retries 408/409/429/5xx automatically with
  exponential backoff honoring `retry-after`; defaults are `max_retries=2` and a
  60s timeout, both configurable on the client constructor.

## Structured output schema constraints (strict mode)

- Root must be an object with defined properties
- `"additionalProperties": false` required on every object
- Max nesting depth 10; max schema text 5,000 characters
- Arrays must define `items`, or use `prefixItems` with `items: false`
- Unsupported: `oneOf`, `allOf`, `not`, `patternProperties`, `if`/`then`/`else`,
  string `pattern`, `format`, `minItems`, `maxItems`, recursive schemas, external `$ref`
