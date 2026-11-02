# Model A/B results, 2026-11-01

- Claims: 40 (16 true, 19 false, 5 uncertain), from `claims-hard.jsonl`
- Repeats per claim: 3
- Reasoning effort: high, sent to every model in its provider's own form. Whether a model honours it varies, so compare the thinking tokens column.
- Prompts are identical; sampling is each model's own default on OpenRouter.
- Every model saw the same cached web evidence per claim.

## Headline

| Model | Accuracy | Completed | Unparsed | Errors | Consistency | Latency mean / p95 | Thinking tokens | Cost per 1k claims | Cost per correct |
|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 99.2% (119/120) | 100.0% | 0 | 0 | 97.5% | 2.9s / 4.6s | 62 | $0.29 | $0.00030 |
| `openai:gpt-6.1-terra` | 100.0% (120/120) | 100.0% | 0 | 0 | 100.0% | 2.4s / 4.8s | 30 | $2.76 | $0.00276 |
| `cerebras:qwen-3.8-27b` | 97.5% (117/120) | 100.0% | 0 | 0 | 100.0% | 0.5s / 1.1s | 243 | $2.96 | $0.00304 |
| `openrouter:qwen/qwen3.8-27b` | 96.7% (116/120) | 100.0% | 0 | 0 | 92.5% | 3.5s / 6.3s | 387 | $1.49 | $0.00154 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | 99.2% (119/120) | 99.2% | 1 | 0 | 97.5% | 4.3s / 10.1s | 534 | $0.74 | $0.00075 |
| `openrouter:minimax/minimax-m3.1-flash` | 92.5% (111/120) | 100.0% | 0 | 0 | 95.0% | 0.9s / 1.6s | 8 | $0.23 | $0.00025 |
| `openrouter:xiaomi/mimo-v2.6-pro` | 98.3% (118/120) | 100.0% | 0 | 0 | 97.5% | 3.2s / 6.3s | 50 | $0.46 | $0.00047 |
| `openrouter:anthropic/claude-haiku-5.5` | 100.0% (120/120) | 100.0% | 0 | 0 | 100.0% | 2.7s / 4.4s | 83 | $0.55 | $0.00055 |
| `openrouter:particle-ai/particle-1` | 97.5% (117/120) | 100.0% | 0 | 0 | 100.0% | 1.9s / 3.3s | 96 | $0.17 | $0.00017 |

Accuracy counts failed calls and unparseable answers as wrong. Completed is the share of attempts that returned a usable verdict, right or wrong. Consistency is the share of claims where every repeat gave the same result. Thinking tokens are the mean reasoning tokens per call. Cost is n/a when a provider reports no cost and `evals/pricing.json` has no price for it.

## Tokens per call (mean)

| Model | Prompt | Completion | of which reasoning |
|---|---|---|---|
| `openai:gpt-6-luna` | 2068 | 175 | 62 |
| `openai:gpt-6.1-terra` | 2068 | 139 | 30 |
| `cerebras:qwen-3.8-27b` | 2416 | 383 | 243 |
| `openrouter:qwen/qwen3.8-27b` | 2209 | 588 | 387 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | 2212 | 980 | 534 |
| `openrouter:minimax/minimax-m3.1-flash` | 2153 | 167 | 8 |
| `openrouter:xiaomi/mimo-v2.6-pro` | 2150 | 228 | 50 |
| `openrouter:anthropic/claude-haiku-5.5` | 3546 | 392 | 83 |
| `openrouter:particle-ai/particle-1` | 2112 | 237 | 96 |

## Precision and recall by verdict

| Model | Verdict | Precision | Recall | Predicted | Actual |
|---|---|---|---|---|---|
| `openai:gpt-6-luna` | true | 100.0% | 100.0% | 48 | 48 |
| `openai:gpt-6-luna` | false | 98.3% | 100.0% | 58 | 57 |
| `openai:gpt-6-luna` | uncertain | 100.0% | 93.3% | 14 | 15 |
| `openai:gpt-6.1-terra` | true | 100.0% | 100.0% | 48 | 48 |
| `openai:gpt-6.1-terra` | false | 100.0% | 100.0% | 57 | 57 |
| `openai:gpt-6.1-terra` | uncertain | 100.0% | 100.0% | 15 | 15 |
| `cerebras:qwen-3.8-27b` | true | 94.1% | 100.0% | 51 | 48 |
| `cerebras:qwen-3.8-27b` | false | 100.0% | 100.0% | 57 | 57 |
| `cerebras:qwen-3.8-27b` | uncertain | 100.0% | 80.0% | 12 | 15 |
| `openrouter:qwen/qwen3.8-27b` | true | 98.0% | 100.0% | 49 | 48 |
| `openrouter:qwen/qwen3.8-27b` | false | 95.0% | 100.0% | 60 | 57 |
| `openrouter:qwen/qwen3.8-27b` | uncertain | 100.0% | 73.3% | 11 | 15 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | true | 100.0% | 100.0% | 48 | 48 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | false | 100.0% | 98.2% | 56 | 57 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | uncertain | 100.0% | 100.0% | 15 | 15 |
| `openrouter:minimax/minimax-m3.1-flash` | true | 96.0% | 100.0% | 50 | 48 |
| `openrouter:minimax/minimax-m3.1-flash` | false | 89.1% | 100.0% | 64 | 57 |
| `openrouter:minimax/minimax-m3.1-flash` | uncertain | 100.0% | 40.0% | 6 | 15 |
| `openrouter:xiaomi/mimo-v2.6-pro` | true | 100.0% | 100.0% | 48 | 48 |
| `openrouter:xiaomi/mimo-v2.6-pro` | false | 96.6% | 100.0% | 59 | 57 |
| `openrouter:xiaomi/mimo-v2.6-pro` | uncertain | 100.0% | 86.7% | 13 | 15 |
| `openrouter:anthropic/claude-haiku-5.5` | true | 100.0% | 100.0% | 48 | 48 |
| `openrouter:anthropic/claude-haiku-5.5` | false | 100.0% | 100.0% | 57 | 57 |
| `openrouter:anthropic/claude-haiku-5.5` | uncertain | 100.0% | 100.0% | 15 | 15 |
| `openrouter:particle-ai/particle-1` | true | 94.1% | 100.0% | 51 | 48 |
| `openrouter:particle-ai/particle-1` | false | 100.0% | 100.0% | 57 | 57 |
| `openrouter:particle-ai/particle-1` | uncertain | 100.0% | 80.0% | 12 | 15 |

## Backends that served each model (OpenRouter)

One model can be served by several backends at very different prices, so a model's cost depends on which ones it landed on.

- `openrouter:qwen/qwen3.8-27b`: Modal 51, ModelRun 30, Wafer 24, Ionstream 15
- `openrouter:nvidia/nemotron-3.5-super-vl`: Crusoe 41, DeepInfra 30, Venice 19, CoreWeave 17, Together 13
- `openrouter:minimax/minimax-m3.1-flash`: DigitalOcean 54, Parasail 39, Together 18, ModelRun 9
- `openrouter:xiaomi/mimo-v2.6-pro`: DeepInfra 120
- `openrouter:anthropic/claude-haiku-5.5`: Azure 120
- `openrouter:particle-ai/particle-1`: Particle AI 120

## Accuracy by category

| Model | compound | contested | counterintuitive | misconception | numeric |
|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 100.0% (18/18) | 93.3% (14/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `openai:gpt-6.1-terra` | 100.0% (18/18) | 100.0% (15/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `cerebras:qwen-3.8-27b` | 100.0% (18/18) | 80.0% (12/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `openrouter:qwen/qwen3.8-27b` | 100.0% (18/18) | 73.3% (11/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `openrouter:nvidia/nemotron-3.5-super-vl` | 100.0% (18/18) | 100.0% (15/15) | 100.0% (21/21) | 95.8% (23/24) | 100.0% (42/42) |
| `openrouter:minimax/minimax-m3.1-flash` | 100.0% (18/18) | 40.0% (6/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `openrouter:xiaomi/mimo-v2.6-pro` | 100.0% (18/18) | 86.7% (13/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `openrouter:anthropic/claude-haiku-5.5` | 100.0% (18/18) | 100.0% (15/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |
| `openrouter:particle-ai/particle-1` | 100.0% (18/18) | 80.0% (12/15) | 100.0% (21/21) | 100.0% (24/24) | 100.0% (42/42) |

## Confusion (rows: true label; columns: what the model returned)

`openai:gpt-6-luna`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 0 | 1 | 14 | 0 | 0 |

`openai:gpt-6.1-terra`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 0 | 0 | 15 | 0 | 0 |

`cerebras:qwen-3.8-27b`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 3 | 0 | 12 | 0 | 0 |

`openrouter:qwen/qwen3.8-27b`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 1 | 3 | 11 | 0 | 0 |

`openrouter:nvidia/nemotron-3.5-super-vl`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 56 | 0 | 1 | 0 |
| uncertain | 0 | 0 | 15 | 0 | 0 |

`openrouter:minimax/minimax-m3.1-flash`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 2 | 7 | 6 | 0 | 0 |

`openrouter:xiaomi/mimo-v2.6-pro`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 0 | 2 | 13 | 0 | 0 |

`openrouter:anthropic/claude-haiku-5.5`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 0 | 0 | 15 | 0 | 0 |

`openrouter:particle-ai/particle-1`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 48 | 0 | 0 | 0 | 0 |
| false | 0 | 57 | 0 | 0 | 0 |
| uncertain | 3 | 0 | 12 | 0 | 0 |

