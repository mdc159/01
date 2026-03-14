# Model & Provider Strategy

## Authenticated Providers (as of 2026-03-14)

| Provider | Auth Method | Status | Primary Use |
|----------|------------|--------|-------------|
| **OpenCode Zen** | API | Active | Claude/GPT proxy, cheap models |
| **OpenAI** | OAuth | Active | Codex (coding), GPT-5.4 (reasoning) |
| **Google** | OAuth | Active | Gemini (frontend, vision, writing) |
| **OpenRouter** | API | Active | Fallback for any model |
| **Groq** | API | Active | Fast inference |
| **xAI** | Env var | Active | Grok models |
| **Perplexity** | API + Env | Active | Search-augmented |
| **Nvidia** | Env var | Active | Nvidia models |
| **Kilo Gateway** | Env var | Active | Multi-provider proxy |

## NOT Using

| Provider | Reason |
|----------|--------|
| **Anthropic (direct)** | Slow, unreliable. Use OpenRouter or OpenCode Zen for Claude models instead. |

## OMO Agent → Model Mapping

**Design principle:** All heavy agents use the same model (`openai/gpt-5.3-codex`) via GPT Pro flat rate. This eliminates model variance as a variable — behavioral differences between agents are purely from their role prompts. When we swap a model later, any delta is cleanly attributable.

| Agent | Role | Model | Provider | Cost |
|-------|------|-------|----------|------|
| **Sisyphus** | Orchestrator | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| **Hephaestus** | Deep coder | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| **Prometheus** | Planner | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| **Metis** | Gap analyzer | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| **Momus** | Reviewer | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| **Atlas** | Executor | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| **Oracle** | Consultant | gpt-5.3-codex (high) | OpenAI Pro | Flat rate |
| **Explore** | Grep/search | gpt-5-nano | OpenCode Zen | Per-token (cheap) |
| **Librarian** | Doc search | gemini-3-flash | OpenCode Zen | Per-token (cheap) |
| **Multimodal** | Vision | gemini-3-flash-preview | Google | Per-token |

## Category → Model Mapping

| Category | Model | Provider | Cost |
|----------|-------|----------|------|
| `ultrabrain` | gpt-5.3-codex (xhigh) | OpenAI Pro | Flat rate |
| `deep` | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| `unspecified-high` | gpt-5.3-codex (high) | OpenAI Pro | Flat rate |
| `unspecified-low` | gpt-5.3-codex (medium) | OpenAI Pro | Flat rate |
| `visual-engineering` | gemini-3.1-pro (high) | Google | Per-token |
| `artistry` | gemini-3.1-pro (high) | Google | Per-token |
| `quick` | gpt-5-nano | OpenCode Zen | Per-token (cheap) |
| `writing` | gemini-3-flash | OpenCode Zen | Per-token (cheap) |

## Cost Structure

| Tier | Models | Cost | When |
|------|--------|------|------|
| **Flat rate** | gpt-5.3-codex (all variants) | $0/token (GPT Pro sub) | All heavy agents + categories |
| **Cheap per-token** | gpt-5-nano, gemini-3-flash (Zen) | ¢ | Explore, Librarian, quick, writing |
| **Per-token** | gemini-3.1-pro, gemini-3-flash-preview | $ | Frontend, vision, artistry |

## Fallback Strategy (TODO)

Current gap: if a provider hits a rate limit mid-task, OMO doesn't automatically failover. Options:
- OpenRouter has multi-provider routing built in
- Custom category fallback chains need investigation
- For now, single-model strategy means rate limits affect everything equally (easy to diagnose)

## Pilot Results (2026-03-14)

### Vanilla OpenCode (`opencode run --format json`)
- Model: `opencode/gpt-5-nano`
- Result: Read plan, applied patch, said DONE
- JSON event stream: fully parseable, includes token counts + tool traces
- Cost: minimal

### OMO Sisyphus (`opencode run --agent sisyphus`)
- Model: `opencode/gpt-5.4` (override via `--model`)
- Result: Full pipeline — todos, skill loading, Momus review, patch, LSP check, py_compile verify
- 12 steps, ~$0.17 total
- JSON event stream: same format, richer (subagent dispatch events)
