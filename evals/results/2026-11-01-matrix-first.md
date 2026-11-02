# Model A/B results, 2026-11-01

- Claims: 36 (14 true, 14 false, 8 uncertain), from `claims.jsonl`
- Repeats per claim: 3
- Reasoning effort: high, sent to every model in its provider's own form. Whether a model honours it varies, so compare the thinking tokens column.
- Prompts are identical; sampling is each model's own default on OpenRouter.
- Every model saw the same cached web evidence per claim.

## Headline

| Model | Accuracy | Completed | Unparsed | Errors | Consistency | Latency mean / p95 | Thinking tokens | Cost per 1k claims | Cost per correct |
|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 94.4% (102/108) | 100.0% | 0 | 0 | 100.0% | 2.4s / 4.0s | 47 | $0.32 | $0.00034 |
| `openai:gpt-6.1-terra` | 94.4% (102/108) | 100.0% | 0 | 0 | 100.0% | 2.2s / 3.1s | 7 | $2.99 | $0.00317 |
| `cerebras:qwen-3.8-27b` | 94.4% (102/108) | 100.0% | 0 | 0 | 100.0% | 0.5s / 1.2s | 202 | $3.30 | $0.00350 |
| `openrouter:qwen/qwen3.8-27b` | 92.6% (100/108) | 100.0% | 0 | 0 | 94.4% | 3.3s / 6.1s | 378 | $1.54 | $0.00167 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | 94.4% (102/108) | 100.0% | 0 | 0 | 100.0% | 7.5s / 32.3s | 520 | $0.65 | $0.00068 |
| `openrouter:minimax/minimax-m3.1-flash` | 94.4% (102/108) | 100.0% | 0 | 0 | 100.0% | 0.9s / 1.6s | 6 | $0.17 | $0.00018 |
| `openrouter:xiaomi/mimo-v2.6-pro` | 91.7% (99/108) | 100.0% | 0 | 0 | 100.0% | 4.6s / 12.4s | 52 | $0.72 | $0.00078 |
| `openrouter:anthropic/claude-haiku-5.5` | 92.6% (100/108) | 100.0% | 0 | 0 | 97.2% | 2.5s / 4.1s | 65 | $0.58 | $0.00063 |
| `openrouter:particle-ai/particle-1` | 95.4% (103/108) | 100.0% | 0 | 0 | 97.2% | 2.3s / 4.5s | 104 | $0.14 | $0.00015 |

Accuracy counts failed calls and unparseable answers as wrong. Completed is the share of attempts that returned a usable verdict, right or wrong. Consistency is the share of claims where every repeat gave the same result. Thinking tokens are the mean reasoning tokens per call. Cost is n/a when a provider reports no cost and `evals/pricing.json` has no price for it.

## Tokens per call (mean)

| Model | Prompt | Completion | of which reasoning |
|---|---|---|---|
| `openai:gpt-6-luna` | 2446 | 156 | 47 |
| `openai:gpt-6.1-terra` | 2446 | 110 | 7 |
| `cerebras:qwen-3.8-27b` | 2836 | 332 | 202 |
| `openrouter:qwen/qwen3.8-27b` | 2629 | 565 | 378 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | 2597 | 691 | 520 |
| `openrouter:minimax/minimax-m3.1-flash` | 2524 | 156 | 6 |
| `openrouter:xiaomi/mimo-v2.6-pro` | 2558 | 228 | 52 |
| `openrouter:anthropic/claude-haiku-5.5` | 4078 | 352 | 65 |
| `openrouter:particle-ai/particle-1` | 2487 | 235 | 104 |

## Precision and recall by verdict

| Model | Verdict | Precision | Recall | Predicted | Actual |
|---|---|---|---|---|---|
| `openai:gpt-6-luna` | true | 87.5% | 100.0% | 48 | 42 |
| `openai:gpt-6-luna` | false | 100.0% | 100.0% | 42 | 42 |
| `openai:gpt-6-luna` | uncertain | 100.0% | 75.0% | 18 | 24 |
| `openai:gpt-6.1-terra` | true | 87.5% | 100.0% | 48 | 42 |
| `openai:gpt-6.1-terra` | false | 100.0% | 100.0% | 42 | 42 |
| `openai:gpt-6.1-terra` | uncertain | 100.0% | 75.0% | 18 | 24 |
| `cerebras:qwen-3.8-27b` | true | 87.5% | 100.0% | 48 | 42 |
| `cerebras:qwen-3.8-27b` | false | 100.0% | 100.0% | 42 | 42 |
| `cerebras:qwen-3.8-27b` | uncertain | 100.0% | 75.0% | 18 | 24 |
| `openrouter:qwen/qwen3.8-27b` | true | 85.7% | 100.0% | 49 | 42 |
| `openrouter:qwen/qwen3.8-27b` | false | 97.7% | 100.0% | 43 | 42 |
| `openrouter:qwen/qwen3.8-27b` | uncertain | 100.0% | 66.7% | 16 | 24 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | true | 87.5% | 100.0% | 48 | 42 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | false | 100.0% | 100.0% | 42 | 42 |
| `openrouter:nvidia/nemotron-3.5-super-vl` | uncertain | 100.0% | 75.0% | 18 | 24 |
| `openrouter:minimax/minimax-m3.1-flash` | true | 87.5% | 100.0% | 48 | 42 |
| `openrouter:minimax/minimax-m3.1-flash` | false | 100.0% | 100.0% | 42 | 42 |
| `openrouter:minimax/minimax-m3.1-flash` | uncertain | 100.0% | 75.0% | 18 | 24 |
| `openrouter:xiaomi/mimo-v2.6-pro` | true | 87.5% | 100.0% | 48 | 42 |
| `openrouter:xiaomi/mimo-v2.6-pro` | false | 93.3% | 100.0% | 45 | 42 |
| `openrouter:xiaomi/mimo-v2.6-pro` | uncertain | 100.0% | 62.5% | 15 | 24 |
| `openrouter:anthropic/claude-haiku-5.5` | true | 87.5% | 100.0% | 48 | 42 |
| `openrouter:anthropic/claude-haiku-5.5` | false | 95.5% | 100.0% | 44 | 42 |
| `openrouter:anthropic/claude-haiku-5.5` | uncertain | 100.0% | 66.7% | 16 | 24 |
| `openrouter:particle-ai/particle-1` | true | 89.4% | 100.0% | 47 | 42 |
| `openrouter:particle-ai/particle-1` | false | 100.0% | 100.0% | 42 | 42 |
| `openrouter:particle-ai/particle-1` | uncertain | 100.0% | 79.2% | 19 | 24 |

## Backends that served each model (OpenRouter)

One model can be served by several backends at very different prices, so a model's cost depends on which ones it landed on.

- `openrouter:qwen/qwen3.8-27b`: ModelRun 37, Wafer 36, Modal 27, Ionstream 6, CoreWeave 2
- `openrouter:nvidia/nemotron-3.5-super-vl`: Crusoe 36, CoreWeave 22, Together 18, Venice 17, DeepInfra 15
- `openrouter:minimax/minimax-m3.1-flash`: Together 54, Parasail 21, DigitalOcean 15, ModelRun 9, Fireworks 3, Nebius 3, SambaNova 3
- `openrouter:xiaomi/mimo-v2.6-pro`: DeepInfra 108
- `openrouter:anthropic/claude-haiku-5.5`: Azure 108
- `openrouter:particle-ai/particle-1`: Particle AI 108

## Confusion (rows: true label; columns: what the model returned)

`openai:gpt-6-luna`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 0 | 18 | 0 | 0 |

`openai:gpt-6.1-terra`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 0 | 18 | 0 | 0 |

`cerebras:qwen-3.8-27b`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 0 | 18 | 0 | 0 |

`openrouter:qwen/qwen3.8-27b`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 7 | 1 | 16 | 0 | 0 |

`openrouter:nvidia/nemotron-3.5-super-vl`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 0 | 18 | 0 | 0 |

`openrouter:minimax/minimax-m3.1-flash`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 0 | 18 | 0 | 0 |

`openrouter:xiaomi/mimo-v2.6-pro`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 3 | 15 | 0 | 0 |

`openrouter:anthropic/claude-haiku-5.5`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 6 | 2 | 16 | 0 | 0 |

`openrouter:particle-ai/particle-1`

| Label | true | false | uncertain | unparsed | error |
|---|---|---|---|---|---|
| true | 42 | 0 | 0 | 0 | 0 |
| false | 0 | 42 | 0 | 0 | 0 |
| uncertain | 5 | 0 | 19 | 0 | 0 |

