# Serafis Quality Evaluation Framework - POC

A minimal proof-of-concept for evaluating Serafis search quality using Gemini 2.5 Flash as an LLM grader.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install google-generativeai
   ```

2. **Run manual tests in Serafis and save data** (see below)

3. **Run evaluation:**
   ```bash
   cd evaluation
   python run_evaluation.py
   ```

---

## Data Collection Instructions

### Test Case 1: Org Search (OpenAI)

1. Go to `app.serafis.ai/#/ai_search`
2. Select "Organizations" tab
3. Search for "OpenAI" in the dropdown
4. Copy the **top 5 results** into `data/openai_org_search.csv`

**CSV Format:**
```csv
mentions,relevance_score,published,episode_title,series,context
3,0.8,2026-01-26,The Hidden Economics Powering AI,a16z Podcast,"OpenAI is extensively discussed..."
2,0.65,2026-01-26,20VC: From Only OpenAI to Die-Hard Anthropic,The Twenty Minute VC,"OpenAI is discussed as Legora's former..."
```

**Columns (in order):**
| Column | Description | Example |
|--------|-------------|---------|
| mentions | Number of mentions (first numeric column) | 3 |
| relevance_score | Decimal score (second numeric column) | 0.8 |
| published | ISO date | 2026-01-26 |
| episode_title | Full episode title | The Hidden Economics Powering AI |
| series | Podcast series name | a16z Podcast |
| context | Context summary | OpenAI is extensively discussed... |

---

### Test Case 2: Ask AI (Bearish Consensus)

1. Go to `app.serafis.ai/#/ai_search`
2. Select "Ask a question" tab
3. Enter: **"What is the bearish consensus on OpenAI into 2026?"**
4. Copy the response into `data/openai_bearish_askia.csv`

**CSV Format:**
```csv
answer,citations
"The bearish consensus on OpenAI into 2026 centers on several key challenges...","[{""id"": 11, ""date"": ""Jun 05, '25"", ""series"": ""The Twenty Minute VC"", ""episode"": ""20VC: Is Chamath Right..."", ""timestamp"": ""44:55"", ""quote"": ""Now, maybe it will...""}]"
```

**Columns:**
| Column | Description |
|--------|-------------|
| answer | The full text answer from Ask AI |
| citations | JSON array of citation objects (escape inner quotes with "") |

**Citation object format:**
```json
{
  "id": 11,
  "date": "Jun 05, '25",
  "series": "The Twenty Minute VC",
  "episode": "20VC: Is Chamath Right...",
  "timestamp": "44:55",
  "quote": "The actual quoted text..."
}
```

---

## Output

The script will:
1. Load test cases from `test_cases.json`
2. Load your manually collected data from `data/*.csv`
3. Use Gemini 2.5 Flash to grade each result
4. Print a formatted report to console
5. Save detailed results to `reports/baseline_YYYYMMDD_HHMMSS.json`

---

## File Structure

```
evaluation/
├── run_evaluation.py       # Main script
├── test_cases.json         # Test case definitions
├── README.md               # This file
├── data/
│   ├── openai_org_search.csv      # Your manual export
│   └── openai_bearish_askia.csv   # Your manual export
└── reports/
    └── baseline_*.json     # Generated reports
```

---

## Grading Dimensions

### Org Search Results (1-5 scale)
- **Relevance**: Is this result actually about the queried entity?
- **Credibility**: Is the speaker an operator/expert?
- **Signal Quality**: Is this substantive or a passing mention?
- **Recency Value**: How valuable is the recency?

### Ask AI Responses (1-5 scale)
- **Citation Accuracy**: Do citations match the quoted content?
- **Groundedness**: Are claims backed by cited sources?
- **Speaker Attribution**: Are speakers identified in the answer?
- **Completeness**: Does the answer address the question fully?
- **Non-Consensus Detection**: Does it surface contrarian views?
