# CSV Templates for Serafis Evaluation

## How to Use

1. **Copy the appropriate template** to the `data/` folder
2. **Rename it** to describe your test case (e.g., `stripe_org_search.csv`)
3. **Replace the example data** with real data from the Serafis UI
4. **Run the evaluation** with the new file

---

## Org Search Template (`org_search_template.csv`)

Use for evaluating organization, person, or theme search results.

### Columns

| Column | Description | Example |
|--------|-------------|---------|
| `relevance_score` | First numeric column (incline graph icon) | `2`, `3`, `4` |
| `score` | Second numeric column (gem icon) | `0.65`, `0.80`, `0.90` |
| `published` | ISO timestamp of episode | `2026-01-27T15:00:00+00:00` |
| `episode_title` | Title of the episode | `The Hidden Economics Powering AI` |
| `series` | Podcast series name | `a16z Podcast` |
| `context` | AI-generated summary of relevance | `OpenAI is discussed extensively...` |

### How to Collect Data

1. Go to `app.serafis.ai/#/ai_search`
2. Select Organizations/Person/Theme tab
3. Search for your entity
4. Copy the results table data into the CSV

---

## Ask AI Template (`ask_ai_template.csv`)

Use for evaluating Ask AI Q&A responses.

### Structure

- **Row 1**: Headers (`answer`, `citations`)
- **Row 2**: Full answer text in column 1, first citation in column 2
- **Row 3+**: Empty column 1, additional citations in column 2

### Citation Format

Each citation should include:
- Source number and date: `1. Jan 27, '26`
- Podcast and episode: `| Podcast Name | Episode Title`
- Timestamp and quote: `HH:MM Quoted text from transcript...`

### How to Collect Data

1. Go to `app.serafis.ai/#/ai_search`
2. Select "Ask a question" tab
3. Enter your question
4. Copy the full answer into the `answer` column
5. Copy each citation (with its quoted text) into separate rows in the `citations` column

---

## Running Evaluations

```bash
# Org search
python run_evaluation.py org_search "EntityName" data/your_org_search.csv

# Ask AI
python run_evaluation.py ask_ai "Your question here?" data/your_ask_ai.csv
```
