from rouge_score import rouge_scorer
from dotenv import load_dotenv
from rag.ingest import load_index
from rag.query import build_query_engine

load_dotenv()

EVAL_DATASET = [
    {
        "question": "What services does ABC Plumbing offer?",
        "ground_truth": "ABC Plumbing offers plumbing installation and repair, pipe replacement, leak detection, water heater services, HVAC installation and repair, drain cleaning, and emergency plumbing services.",
    },
    {
        "question": "What are the business hours?",
        "ground_truth": "Monday to Friday 7AM to 6PM, Saturday 8AM to 2PM, Sunday closed except for emergencies.",
    },
    {
        "question": "How much does a service call cost?",
        "ground_truth": "The service call fee is $75, which is waived if work is performed.",
    },
    {
        "question": "What is the labor rate for plumbing work?",
        "ground_truth": "The plumbing labor rate is $95 per hour.",
    },
    {
        "question": "Do you provide free estimates?",
        "ground_truth": "Yes, free estimates are provided for installations and projects over $500.",
    },
    {
        "question": "What areas do you serve?",
        "ground_truth": "Austin and surrounding areas including Round Rock, Cedar Park, Pflugerville, Georgetown, and Kyle within a 30-mile radius.",
    },
    {
        "question": "Is there a warranty on the work?",
        "ground_truth": "Yes, all labor is warranted for 12 months and parts carry manufacturer warranty of 1 to 5 years.",
    },
    {
        "question": "What payment methods are accepted?",
        "ground_truth": "Cash, check, and all major credit cards. Financing available for projects over $2,000.",
    },
    {
        "question": "Are you available for emergencies?",
        "ground_truth": "Yes, emergency services are available 24/7 at 1.5x the standard rate.",
    },
    {
        "question": "How long does a typical plumbing repair take?",
        "ground_truth": "Most plumbing repairs take 1 to 2 hours.",
    },
]


def run_evals() -> None:
    print("Loading index and building query engine...")
    index = load_index()
    engine = build_query_engine(index)

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = []

    print(f"\nRunning {len(EVAL_DATASET)} eval questions...\n")
    print(f"{'Question':<45} {'RougeL':>8}")
    print("-" * 55)

    for item in EVAL_DATASET:
        q = item["question"]
        gt = item["ground_truth"]

        response = engine.query(q)
        contexts = [node.get_content() for node in response.source_nodes]
        combined_context = " ".join(contexts)

        result = scorer.score(gt, combined_context)
        rougeL = result["rougeL"].fmeasure
        scores.append(rougeL)

        short_q = q[:44]
        print(f"{short_q:<45} {rougeL:>8.3f}")

    avg = sum(scores) / len(scores)
    print("-" * 55)
    print(f"\nRAGAS Baseline (RougeL, no LLM needed):")
    print(f"  Average RougeL: {avg:.3f}")
    print()
    print("Interpretation:")
    print("  > 0.3  acceptable retrieval overlap")
    print("  > 0.5  good retrieval overlap")
    print("  > 0.7  strong retrieval overlap")
    print()
    print("Note: faithfulness + answer_relevancy run in Phase 2 with Ollama.")


if __name__ == "__main__":
    run_evals()