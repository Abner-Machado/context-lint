# context-lint

Context budget auditor for agent prompts. Measures token usage, detects wasted tokens, and suggests trims before your prompt hits the LLM.

**Zero dependencies.** Python 3.8+, no pip install, no network, no API call.

## Why

AI agents burn token budget on filler phrases, excessive blank lines, and duplicate blocks. context-lint catches this waste before your prompt reaches the model — saving cost and context window for what actually matters.

## Usage

```bash
python context_lint.py path/to/prompt.md
python context_lint.py path/to/prompt.md --max-tokens 4000
python context_lint.py path/to/prompt.md --json
```

## Example

```
context-lint v1.0.0
File: /prompts/system.md
Budget: OK (3142/8000 tokens)
Waste: 148 tokens (4.7%)

--- Findings (3) ---
  [LOW] L12: Filler phrase detected at line 12
  [LOW] L47: Filler phrase detected at line 47
  [LOW] L89: Line 89 is 344 chars (200+). Consider breaking.
```

## What it catches

- Filler phrases ("feel free to", "let me know if", "as an AI")
- Excessive blank lines (3+ consecutive)
- Lines over 200 characters
- Near-duplicate content blocks

## Budget recommendations

| Context window | Clean threshold |
|---------------|-----------------|
| 4K tokens | < 10% waste |
| 8K tokens | < 8% waste |
| 32K+ tokens | < 5% waste |

## License

MIT