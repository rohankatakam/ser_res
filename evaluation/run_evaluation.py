"""
Serafis Quality Evaluation Framework - POC
Uses Gemini 2.5 Flash to grade search results and Ask AI responses.

Usage:
    # Grade org search results (evaluates top 5 by score)
    python run_evaluation.py org_search "OpenAI" data/openai_org_search.csv
    
    # Grade Ask AI response
    python run_evaluation.py ask_ai "What is the bearish consensus on OpenAI?" data/openai_bearish_askia.csv
"""

import json
import csv
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in environment.")
    print("   Please create a .env file with: GEMINI_API_KEY=your_key_here")
    sys.exit(1)

MODEL_NAME = "gemini-2.5-flash"

# Configure Gemini with max tokens
genai.configure(api_key=GEMINI_API_KEY)

# Model configuration with max context
generation_config = {
    "temperature": 0.3,  # Lower for more consistent grading
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 65535,  # Max output
}

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
)


def load_csv_data(csv_path: str) -> list[dict]:
    """Load CSV data into list of dicts."""
    if not os.path.exists(csv_path):
        print(f"❌ Data file not found: {csv_path}")
        return []
    
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_and_sort_org_search(csv_path: str) -> list[dict]:
    """
    Load org search CSV and sort by score (descending).
    This ensures we evaluate the TOP 5 results as ranked by the system.
    """
    data = load_csv_data(csv_path)
    if not data:
        return []
    
    # Sort by score column (descending) - higher score = better ranking
    # Handle both 'score' and 'relevance_score' column names
    def get_score(row):
        score_val = row.get('score', row.get('relevance_score', '0'))
        try:
            return float(score_val)
        except (ValueError, TypeError):
            return 0.0
    
    sorted_data = sorted(data, key=get_score, reverse=True)
    return sorted_data


def load_ask_ai_data(csv_path: str) -> dict:
    """
    Load Ask AI data from CSV with format:
    - Row 1: headers (answer, citations)
    - Row 2: answer text in column 1, first citation in column 2
    - Row 3+: empty column 1, additional citations in column 2
    
    Returns dict with 'answer' and 'citations' keys.
    """
    if not os.path.exists(csv_path):
        print(f"❌ Data file not found: {csv_path}")
        return {}
    
    answer = ""
    citations = []
    
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        headers = next(reader, None)  # Skip header row
        
        for i, row in enumerate(reader):
            if len(row) >= 1 and row[0].strip():
                # First non-empty answer column
                if not answer:
                    answer = row[0].strip()
            
            if len(row) >= 2 and row[1].strip():
                # Collect all citations from column 2
                citations.append(row[1].strip())
    
    return {
        "answer": answer,
        "citations": "\n".join(citations)
    }


def grade_org_search_result(result: dict, query: str, current_date: str) -> dict:
    """Use Gemini to grade a single org search result."""
    
    # Get score values for context
    relevance_score = result.get('relevance_score', result.get('mentions', 'N/A'))
    score = result.get('score', 'N/A')
    
    prompt = f"""You are an expert evaluator for an institutional investor search product.

IMPORTANT: The current date is {current_date}. Use this to accurately assess recency.

TASK: Grade this search result for the query "{query}"

SEARCH RESULT:
- System Relevance Score: {relevance_score}
- System Score: {score}
- Published: {result.get('published', 'N/A')}
- Episode Title: {result.get('episode_title', 'N/A')}
- Series: {result.get('series', 'N/A')}
- Context Summary: {result.get('context', 'N/A')}

Grade this result on a 1-5 scale for each dimension:

1. RELEVANCE (1-5): Is this result actually about {query}? 
   - 5 = Primary focus of episode, {query} leadership/executives speaking
   - 4 = Significant discussion of {query} strategy or business
   - 3 = Meaningful discussion but not primary focus
   - 2 = Brief but substantive mention
   - 1 = Passing mention only

2. CREDIBILITY (1-5): Based on the context, is the speaker likely an operator/expert?
   - 5 = Operator (CEO/founder/executive of {query} or direct competitor)
   - 4 = Domain expert with direct experience in {query}'s industry
   - 3 = Informed analyst/investor with track record
   - 2 = Journalist or generalist commentator
   - 1 = Unknown or low-credibility source

3. SIGNAL_QUALITY (1-5): Is this substantive or surface-level?
   - 5 = Novel strategic insights, exclusive information, predictions
   - 4 = Deep analysis with concrete data points
   - 3 = Useful information but common knowledge
   - 2 = General commentary without specifics
   - 1 = Generic mention, no new information

4. RECENCY_VALUE (1-5): How valuable is the recency given the topic? (Current date: {current_date})
   - 5 = Very recent (< 1 month old) and covers time-sensitive developments
   - 4 = Recent (1-3 months old) and still highly relevant
   - 3 = Moderately recent (3-6 months old), core insights still valid
   - 2 = Older (6-12 months old), may be outdated
   - 1 = Stale (> 12 months old) or covers outdated information

5. CONTEXT_QUALITY (1-5): Is the context summary useful and accurate?
   - 5 = Context clearly explains WHY this result is relevant to {query}, identifies speaker, and previews key insights
   - 4 = Context is helpful and explains relevance with some specific details
   - 3 = Context is generic but adequate, could apply to many results
   - 2 = Context is vague or doesn't clearly explain relevance to {query}
   - 1 = Context is missing, misleading, or provides no useful information

Return your evaluation as JSON:
{{
    "relevance": <1-5>,
    "credibility": <1-5>,
    "signal_quality": <1-5>,
    "recency_value": <1-5>,
    "context_quality": <1-5>,
    "overall_score": <1-5>,
    "is_high_signal": <true if overall >= 4>,
    "rationale": "<brief 1-2 sentence explanation>"
}}

Return ONLY valid JSON, no other text."""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        return {
            "relevance": 0,
            "credibility": 0,
            "signal_quality": 0,
            "recency_value": 0,
            "context_quality": 0,
            "overall_score": 0,
            "is_high_signal": False,
            "rationale": f"Error grading: {str(e)}",
            "error": True
        }


def grade_ask_ai_response(response_data: dict, query: str) -> dict:
    """Use Gemini to grade an Ask AI response."""
    
    prompt = f"""You are an expert evaluator for an institutional investor AI Q&A product.

TASK: Grade this Ask AI response for the query:
"{query}"

ANSWER:
{response_data.get('answer', 'N/A')}

CITATIONS (each citation includes source info, timestamp, and quoted content):
{response_data.get('citations', 'N/A')}

Grade this response on a 1-5 scale for each dimension:

1. CITATION_ACCURACY (1-5): Do citations appear to match the quoted content?
   - 5 = All citations clearly support their claims with exact quotes
   - 4 = Most citations are accurate with minor inconsistencies
   - 3 = Citations generally support claims but some are tangential
   - 2 = Several citations don't match claims well
   - 1 = Citations don't match claims or are missing

2. GROUNDEDNESS (1-5): Are claims backed by cited sources?
   - 5 = Every substantive claim has supporting citation
   - 4 = Most claims supported, only minor points uncited
   - 3 = Core claims supported but some unsupported assertions
   - 2 = Many claims lack citations
   - 1 = Mostly unsupported claims

3. SPEAKER_ATTRIBUTION (1-5): Are speakers identified in the answer?
   - 5 = All key speakers named with role/title and credibility context
   - 4 = Most speakers identified with some context
   - 3 = Some speakers named but lacking context
   - 2 = Few speakers identified
   - 1 = No speaker attribution

4. COMPLETENESS (1-5): Does the answer address the question fully?
   - 5 = Comprehensive, addresses all aspects with depth
   - 4 = Good coverage, addresses main points well
   - 3 = Adequate but missing some important aspects
   - 2 = Partial answer, significant gaps
   - 1 = Superficial or largely misses the question

5. NON_CONSENSUS_DETECTION (1-5): Does it surface contrarian/non-consensus views?
   - 5 = Explicitly identifies and labels non-consensus opinions
   - 4 = Surfaces contrarian views though not explicitly labeled
   - 3 = Includes some alternative perspectives
   - 2 = Mostly mainstream consensus views
   - 1 = Only consensus views, no contrarian perspectives

Return your evaluation as JSON:
{{
    "citation_accuracy": <1-5>,
    "groundedness": <1-5>,
    "speaker_attribution": <1-5>,
    "completeness": <1-5>,
    "non_consensus_detection": <1-5>,
    "overall_score": <1-5>,
    "is_institutional_grade": <true if overall >= 4 and citation_accuracy >= 4>,
    "rationale": "<brief 1-2 sentence explanation>"
}}

Return ONLY valid JSON, no other text."""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        return {
            "citation_accuracy": 0,
            "groundedness": 0,
            "speaker_attribution": 0,
            "completeness": 0,
            "non_consensus_detection": 0,
            "overall_score": 0,
            "is_institutional_grade": False,
            "rationale": f"Error grading: {str(e)}",
            "error": True
        }


def run_org_search_evaluation(query: str, csv_path: str) -> dict:
    """Run evaluation for an org search query."""
    
    print(f"\n📊 Evaluating Org Search: \"{query}\"")
    print(f"   Data file: {csv_path}")
    
    # Load and SORT by score (descending) - evaluates TOP 5 by system ranking
    data = load_and_sort_org_search(csv_path)
    if not data:
        return {"error": "No data found"}
    
    # Get current date for accurate recency evaluation
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"   Total results in CSV: {len(data)}")
    print(f"   Current date for recency: {current_date}")
    print(f"   Evaluating TOP 5 by score (system ranking)...")
    
    results = {
        "type": "org_search",
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "current_date": current_date,
        "grades": []
    }
    
    # Grade top 5 results (sorted by score)
    for i, result in enumerate(data[:5]):
        score_val = result.get('score', result.get('relevance_score', 'N/A'))
        print(f"   Grading result {i+1}/5 (score: {score_val})...")
        grade = grade_org_search_result(result, query, current_date)
        grade["rank"] = i + 1
        grade["system_score"] = score_val
        grade["episode_title"] = result.get("episode_title", "")
        grade["published"] = result.get("published", "")
        results["grades"].append(grade)
    
    # Calculate metrics
    if results["grades"]:
        valid_grades = [g for g in results["grades"] if not g.get("error")]
        if valid_grades:
            avg_overall = sum(g.get("overall_score", 0) for g in valid_grades) / len(valid_grades)
            precision = sum(1 for g in valid_grades if g.get("is_high_signal", False)) / len(valid_grades)
            results["metrics"] = {
                "avg_overall_score": round(avg_overall, 2),
                "precision_at_5": round(precision * 100, 1),
                "results_graded": len(valid_grades)
            }
    
    return results


def run_ask_ai_evaluation(query: str, csv_path: str) -> dict:
    """Run evaluation for an Ask AI query."""
    
    print(f"\n📊 Evaluating Ask AI: \"{query}\"")
    print(f"   Data file: {csv_path}")
    
    # Use the multi-row citation loader
    response_data = load_ask_ai_data(csv_path)
    if not response_data or not response_data.get("answer"):
        return {"error": "No data found or answer is empty"}
    
    print(f"   Answer length: {len(response_data['answer'])} chars")
    print(f"   Citations found: {response_data['citations'].count(chr(10)) + 1 if response_data['citations'] else 0}")
    
    results = {
        "type": "ask_ai",
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "answer_preview": response_data['answer'][:200] + "...",
        "grades": []
    }
    
    # Grade the response
    print("   Grading Ask AI response...")
    grade = grade_ask_ai_response(response_data, query)
    results["grades"].append(grade)
    
    # Extract metrics
    if not grade.get("error"):
        results["metrics"] = {
            "citation_accuracy": grade.get("citation_accuracy", 0),
            "groundedness": grade.get("groundedness", 0),
            "speaker_attribution": grade.get("speaker_attribution", 0),
            "completeness": grade.get("completeness", 0),
            "non_consensus_detection": grade.get("non_consensus_detection", 0),
            "overall_score": grade.get("overall_score", 0),
            "is_institutional_grade": grade.get("is_institutional_grade", False)
        }
    
    return results


def print_org_search_report(results: dict):
    """Print formatted report for org search."""
    
    print(f"\n{'─'*60}")
    print(f"📊 ORG SEARCH: \"{results['query']}\"")
    print(f"{'─'*60}")
    
    print("\nTop 5 Results (by system score):")
    for grade in results.get("grades", []):
        if grade.get("error"):
            print(f"   {grade['rank']}. ❌ Error: {grade.get('rationale', 'Unknown')}")
            continue
            
        signal = "✅ HIGH" if grade.get("is_high_signal") else "⚠️ LOW"
        print(f"\n   {grade['rank']}. [{signal}] System Score: {grade.get('system_score', 'N/A')} → Our Grade: {grade.get('overall_score', 'N/A')}/5")
        print(f"      Episode: {grade.get('episode_title', 'N/A')[:50]}...")
        print(f"      Relevance: {grade.get('relevance', 'N/A')}/5 | Credibility: {grade.get('credibility', 'N/A')}/5")
        print(f"      Signal: {grade.get('signal_quality', 'N/A')}/5 | Recency: {grade.get('recency_value', 'N/A')}/5 | Context: {grade.get('context_quality', 'N/A')}/5")
        print(f"      💬 {grade.get('rationale', 'N/A')}")
    
    if "metrics" in results:
        print(f"\n📈 METRICS:")
        print(f"   Precision@5: {results['metrics']['precision_at_5']}%")
        print(f"   Avg Score: {results['metrics']['avg_overall_score']}/5")
        print(f"   Results Graded: {results['metrics']['results_graded']}")


def print_ask_ai_report(results: dict):
    """Print formatted report for Ask AI."""
    
    print(f"\n{'─'*60}")
    print(f"📊 ASK AI: \"{results['query'][:50]}...\"")
    print(f"{'─'*60}")
    
    if results.get("grades"):
        grade = results["grades"][0]
        
        if grade.get("error"):
            print(f"\n❌ Error: {grade.get('rationale', 'Unknown')}")
            return
        
        quality = "✅ INSTITUTIONAL GRADE" if grade.get("is_institutional_grade") else "⚠️ NEEDS IMPROVEMENT"
        print(f"\n   Overall Quality: {quality}")
        print(f"   Overall Score: {grade.get('overall_score', 'N/A')}/5")
        
        print(f"\n   Dimension Scores:")
        print(f"   ├─ Citation Accuracy:     {grade.get('citation_accuracy', 'N/A')}/5")
        print(f"   ├─ Groundedness:          {grade.get('groundedness', 'N/A')}/5")
        print(f"   ├─ Speaker Attribution:   {grade.get('speaker_attribution', 'N/A')}/5")
        print(f"   ├─ Completeness:          {grade.get('completeness', 'N/A')}/5")
        print(f"   └─ Non-Consensus:         {grade.get('non_consensus_detection', 'N/A')}/5")
        
        print(f"\n   💬 {grade.get('rationale', 'N/A')}")


def generate_org_search_markdown(results: dict) -> str:
    """Generate markdown report for org search evaluation."""
    
    md = []
    md.append(f"# Org Search Evaluation: \"{results['query']}\"")
    md.append(f"\n**Timestamp:** {results['timestamp']}")
    md.append(f"\n**Evaluation Method:** Top 5 results sorted by system score (descending)")
    
    # Summary metrics
    if "metrics" in results:
        md.append("\n## Summary Metrics")
        md.append("")
        md.append("| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| **Precision@5** | {results['metrics']['precision_at_5']}% |")
        md.append(f"| **Avg Grade** | {results['metrics']['avg_overall_score']}/5 |")
        md.append(f"| **Results Graded** | {results['metrics']['results_graded']} |")
    
    # Results table
    md.append("\n## Top 5 Results (by System Score)")
    md.append("")
    md.append("| Rank | System Score | Our Grade | High Signal | Episode |")
    md.append("|------|--------------|-----------|-------------|---------|")
    
    for grade in results.get("grades", []):
        if grade.get("error"):
            md.append(f"| {grade['rank']} | - | ❌ Error | - | - |")
            continue
        
        signal = "✅" if grade.get("is_high_signal") else "⚠️"
        episode = grade.get('episode_title', 'N/A')[:40] + "..."
        md.append(f"| {grade['rank']} | {grade.get('system_score', 'N/A')} | {grade.get('overall_score', 'N/A')}/5 | {signal} | {episode} |")
    
    # Detailed grades
    md.append("\n## Detailed Grades")
    
    for grade in results.get("grades", []):
        if grade.get("error"):
            continue
        
        signal_label = "✅ HIGH SIGNAL" if grade.get("is_high_signal") else "⚠️ LOW SIGNAL"
        md.append(f"\n### {grade['rank']}. {grade.get('episode_title', 'N/A')[:60]}")
        md.append(f"\n**{signal_label}** | System Score: {grade.get('system_score', 'N/A')} | Our Grade: {grade.get('overall_score', 'N/A')}/5")
        md.append(f"\n**Published:** {grade.get('published', 'N/A')}")
        md.append("")
        md.append("| Dimension | Score |")
        md.append("|-----------|-------|")
        md.append(f"| Relevance | {grade.get('relevance', 'N/A')}/5 |")
        md.append(f"| Credibility | {grade.get('credibility', 'N/A')}/5 |")
        md.append(f"| Signal Quality | {grade.get('signal_quality', 'N/A')}/5 |")
        md.append(f"| Recency Value | {grade.get('recency_value', 'N/A')}/5 |")
        md.append(f"| Context Quality | {grade.get('context_quality', 'N/A')}/5 |")
        md.append(f"\n> **Rationale:** {grade.get('rationale', 'N/A')}")
    
    return "\n".join(md)


def generate_ask_ai_markdown(results: dict) -> str:
    """Generate markdown report for Ask AI evaluation."""
    
    md = []
    md.append(f"# Ask AI Evaluation")
    md.append(f"\n**Query:** \"{results['query']}\"")
    md.append(f"\n**Timestamp:** {results['timestamp']}")
    
    if results.get("grades"):
        grade = results["grades"][0]
        
        if grade.get("error"):
            md.append(f"\n## ❌ Error\n\n{grade.get('rationale', 'Unknown error')}")
            return "\n".join(md)
        
        # Verdict
        quality = "✅ INSTITUTIONAL GRADE" if grade.get("is_institutional_grade") else "⚠️ NEEDS IMPROVEMENT"
        md.append(f"\n## Verdict: {quality}")
        md.append(f"\n**Overall Score:** {grade.get('overall_score', 'N/A')}/5")
        
        # Dimension scores table
        md.append("\n## Dimension Scores")
        md.append("")
        md.append("| Dimension | Score | Description |")
        md.append("|-----------|-------|-------------|")
        md.append(f"| Citation Accuracy | {grade.get('citation_accuracy', 'N/A')}/5 | Do citations match quoted content? |")
        md.append(f"| Groundedness | {grade.get('groundedness', 'N/A')}/5 | Are claims backed by sources? |")
        md.append(f"| Speaker Attribution | {grade.get('speaker_attribution', 'N/A')}/5 | Are speakers identified? |")
        md.append(f"| Completeness | {grade.get('completeness', 'N/A')}/5 | Does it fully answer the question? |")
        md.append(f"| Non-Consensus | {grade.get('non_consensus_detection', 'N/A')}/5 | Does it surface contrarian views? |")
        
        # Rationale
        md.append("\n## Analysis")
        md.append(f"\n{grade.get('rationale', 'N/A')}")
        
        # Answer preview
        if results.get("answer_preview"):
            md.append("\n## Answer Preview")
            md.append(f"\n> {results['answer_preview']}")
    
    return "\n".join(md)


def save_results(results: dict, output_dir: str = "reports"):
    """Save results to markdown file."""
    Path(output_dir).mkdir(exist_ok=True)
    
    query_slug = results["query"][:30].replace(" ", "_").replace("/", "_").replace("?", "").replace('"', '')
    filename = f"{results['type']}_{query_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_path = os.path.join(output_dir, filename)
    
    # Generate markdown
    if results["type"] == "org_search":
        markdown = generate_org_search_markdown(results)
    else:
        markdown = generate_ask_ai_markdown(results)
    
    with open(output_path, 'w') as f:
        f.write(markdown)
    
    # Also save JSON for programmatic access
    json_path = output_path.replace('.md', '.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved:")
    print(f"   Markdown: {output_path}")
    print(f"   JSON: {json_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Serafis Quality Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Grade org search results (evaluates TOP 5 by score)
  python run_evaluation.py org_search "OpenAI" data/openai_org_search.csv
  
  # Grade Ask AI response  
  python run_evaluation.py ask_ai "What is the bearish consensus on OpenAI?" data/openai_bearish.csv
  
  # Grade with custom output directory
  python run_evaluation.py org_search "Stripe" data/stripe_search.csv --output ./my_reports
        """
    )
    
    parser.add_argument(
        "eval_type",
        choices=["org_search", "ask_ai"],
        help="Type of evaluation to run"
    )
    
    parser.add_argument(
        "query",
        help="Search query (org name for org_search, question for ask_ai)"
    )
    
    parser.add_argument(
        "csv_path",
        help="Path to CSV file with data to evaluate"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="reports",
        help="Output directory for results (default: reports)"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    
    args = parser.parse_args()
    
    print("\n🚀 Serafis Quality Evaluation")
    print("="*60)
    
    # Run appropriate evaluation
    if args.eval_type == "org_search":
        results = run_org_search_evaluation(args.query, args.csv_path)
        print_org_search_report(results)
    else:
        results = run_ask_ai_evaluation(args.query, args.csv_path)
        print_ask_ai_report(results)
    
    # Save results
    if not args.no_save and not results.get("error"):
        save_results(results, args.output)
    
    print("\n" + "="*60)
    print("✅ Evaluation complete!")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("""
Serafis Quality Evaluation Framework

Usage:
  python run_evaluation.py org_search "<org_name>" <csv_path>
  python run_evaluation.py ask_ai "<question>" <csv_path>

Examples:
  python run_evaluation.py org_search "OpenAI" data/openai_org_search.csv
  python run_evaluation.py ask_ai "What is the bearish consensus on OpenAI?" data/openai_bearish_askia.csv

Note: Org search results are sorted by score (descending) before evaluating top 5.

Run with --help for more options.
        """)
    else:
        main()
