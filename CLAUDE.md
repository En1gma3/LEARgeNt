# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LearnMate is an intelligent learning assistant that uses LLM-powered Socratic dialogue with structured knowledge representation (three-anchor system) for deep learning of concepts.

## Commands

### Environment Setup
```bash
conda activate leargent    # 必须先激活 conda 环境
```

### Run Application
```bash
python -m cli                    # Start interactive mode
python -m cli learn 区块链       # Learn a specific concept directly
```

### Run Tests
```bash
python tests.py                  # Run all tests
python tests.py -v              # Verbose output
python tests.py TestLogger      # Run specific test class
```

### Configuration
Environment variables override `config/config.yaml`:
- `LLM_PROVIDER` - openai/anthropic/ollama/minimax/mock
- `LLM_MODEL` - model name
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` - API keys
- `LEARNMATE_LOG_LEVEL` - DEBUG/INFO/WARNING/ERROR

## Architecture

### Learning Flow
1. **EXPLAINING** - AI explains concept using anchors
2. **Q_A_LOOP** - User asks questions (multi-turn context preserved)
3. **SUMMARIZING** - Generate structured summary
4. **GUIDING** - Classic Socratic questioning

### Three-Anchor Knowledge Structure
Every concept has anchors built by LLM:
- **topic_anchor**: Larger theme/domain
- **dependency_anchors**: Pre-requisite concepts
- **semantic_anchor**: One-sentence definition
- **contrast_anchor** / **example_anchor**: Optional

### Key Components
| Directory | Purpose |
|-----------|---------|
| `agent/` | Core learning agent - dialogue, socratic, anchors, LLM clients |
| `cli/` | Interactive CLI with arrow key navigation |
| `knowledge/` | SQLite knowledge base with FTS5 search |
| `memory/` | Short-term (sessions) and long-term (learned terms) memory |
| `parser/` | Content parsers for PDF, news, companies, industries |
| `extractor/` | Term extraction with LLM, NLP, statistical methods |

### Data Storage
| File | Purpose |
|------|---------|
| `data/knowledge.db` | SQLite - terms, tags, relations |
| `data/sessions.json` | Session history |
| `data/logs/learnmate.log` | Application logs |
| `data/logs/llm.log` | LLM request/response logs |

## Design Patterns

- **Factory pattern**: `ParserFactory`, `create_llm_client()`
- **State machine**: `DialogueState` enum manages conversation flow
- **Dataclasses**: Models use `@dataclass` decorators
- **ABC pattern**: Base extractors are abstract classes

## Important Notes

- Config priority: Env vars > `config/config.yaml` > `~/.learnmate/config.yaml`
- LLM client logs requests to `data/logs/llm.log`
- Multi-turn conversation uses `message_history` field in `SocraticSession`
- Arrow selector (`cli/selector.py`) supports cursor navigation for menus
