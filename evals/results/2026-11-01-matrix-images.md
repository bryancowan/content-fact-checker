# Image extraction A/B results, 2026-11-01

- Images: 5, from `images.jsonl`
- Repeats per image: 3
- Reasoning effort: high, sent to every model in its provider's own form.
- Measures claim extraction only; the verdict step is text and is covered by `run_ab.py`.

| Model | Recall | Completed | Extras per image | Injection followed | Unparsed | Errors | Latency mean / p95 | Thinking tokens | Cost per 1k images |
|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 100.0% (33/33) | 100.0% | 0.33 | 0 | 0 | 0 | 2.4s / 4.9s | 118 | $0.16 |
| `openai:gpt-6.1-terra` | 100.0% (33/33) | 100.0% | 0.40 | 0 | 0 | 0 | 2.1s / 4.4s | 64 | $1.34 |
| `cerebras:qwen-3.8-27b` | 100.0% (33/33) | 100.0% | 1.47 | 0 | 0 | 0 | 0.9s / 2.0s | 498 | $1.66 |
| `openrouter:qwen/qwen3.8-27b` | 100.0% (33/33) | 100.0% | 1.20 | 0 | 0 | 0 | 1.3s / 1.9s | 173 | $0.65 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | 100.0% (33/33) | 100.0% | 0.73 | 0 | 0 | 0 | 3.9s / 11.3s | 760 | $0.49 |
| `openrouter:minimax/minimax-m3.1-flash` | 100.0% (33/33) | 100.0% | 1.07 | 0 | 0 | 0 | 1.2s / 2.2s | 123 | $0.17 |
| `openrouter:xiaomi/mimo-v2.6-pro` | 100.0% (33/33) | 100.0% | 0.93 | 0 | 0 | 0 | 4.0s / 20.6s | 60 | $0.17 |
| `openrouter:anthropic/claude-haiku-5.5` | 100.0% (33/33) | 100.0% | 1.13 | 0 | 0 | 0 | 2.5s / 4.7s | 110 | $0.20 |
| `openrouter:particle-ai/particle-1` | 100.0% (33/33) | 100.0% | 1.07 | 0 | 0 | 0 | 1.5s / 2.8s | 124 | $0.11 |

Recall is the share of expected claims whose keywords all appear in an extracted claim. Extras are extracted claims that match nothing expected, so a high count can mean invented claims or true ones the manifest doesn't list; read the raw `.jsonl` before judging. A model without vision support shows up as errors.
