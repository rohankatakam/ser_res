# Deprecated Code

This folder contains deprecated code that has been superseded by newer implementations.
These files are kept for reference only. **Do not use in new code.**

## Contents

### `llm_judge.py`

**Deprecated:** 2026-02-09

**Reason:** Replaced by multi-LLM judge infrastructure.

**Replacement:**
- `evaluation/judges/` - Multi-LLM orchestration package
- `evaluation/criteria/` - Modular criterion definitions

**Key improvements in the new system:**
- Multi-provider support (OpenAI, Gemini, Anthropic) via LiteLLM
- Per-criterion LLM calls for maximum modularity
- Two-stage aggregation (within-model, then cross-model)
- Configurable N samples per judge (default: 3)
- Temperature 0.8 (research-backed for better calibration)
- Consensus metrics and uncertainty reporting
- Graceful degradation if one provider fails

**Migration example:**

```python
# Old usage:
from llm_judge import evaluate_with_llm
result = evaluate_with_llm(profile, response, test_case)

# New usage:
from judges import evaluate_all_criteria, load_judge_config
from criteria import get_criteria_for_test

criteria = get_criteria_for_test(test_case)
config = load_judge_config()
results = await evaluate_all_criteria(criteria, profile, response, test_case, config)
```
