import json
import datetime
from src.agent import run_agent

BENCHMARK = [
    {
        "id": "eval_001",
        "query": "Is the vessel EBANO sanctioned?",
        "expected": {
            "entity_found": True,
            "entity_name": "EBANO",
            "entity_type": "Vessel",
            "sources": ["ofac"],
            "programs": ["CUBA"],
            "imo": "7406784",
            "keywords": ["sanctioned", "CUBA", "Panama", "cargo"]
        }
    },
    {
        "id": "eval_002",
        "query": "What sanctions programs is Al Qaeda listed under?",
        "expected": {
            "entity_found": True,
            "entity_name": "Al Qaeda",
            "entity_type": "Organisation",
            "sources": ["ofac", "un", "eu"],
            "programs": ["SDGT", "FTO"],
            "keywords": ["SDGT", "FTO", "terrorist", "multiple"]
        }
    },
    {
        "id": "eval_003",
        "query": "What is Osama Bin Laden's date of birth and nationality?",
        "expected": {
            "entity_found": True,
            "entity_name": "Bin Laden",
            "entity_type": "Person",
            "keywords": ["1957", "SDGT"]
        }
    },
    {
        "id": "eval_004",
        "query": "How many vessels are sanctioned under the Iran program?",
        "expected": {
            "entity_found": True,
            "entity_type": "Vessel",
            "programs": ["IRAN"],
            "keywords": ["547", "vessel", "Iran"]
        }
    },
    {
        "id": "eval_005",
        "query": "Is there a sanctioned entity called Hamas and which lists does it appear on?",
        "expected": {
            "entity_found": True,
            "entity_name": "Hamas",
            "entity_type": "Organisation",
            "sources": ["ofac", "eu"],
            "keywords": ["Hamas", "sanctioned", "SDGT"]
        }
    },
]

def score_response(answer: str, expected: dict) -> dict:
    answer_lower = answer.lower()
    results = {}

    # keyword checks
    keyword_hits = []
    keyword_misses = []
    for kw in expected.get("keywords", []):
        if kw.lower() in answer_lower:
            keyword_hits.append(kw)
        else:
            keyword_misses.append(kw)

    results["keyword_hit_rate"] = len(keyword_hits) / len(expected["keywords"]) if expected.get("keywords") else 1.0
    results["keyword_hits"] = keyword_hits
    results["keyword_misses"] = keyword_misses

    # entity found check
    if "entity_name" in expected:
        name_parts = expected["entity_name"].lower().split()
        results["entity_found"] = all(p in answer_lower for p in name_parts)
    else:
        results["entity_found"] = True

    # overall pass: keyword hit rate >= 0.7 and entity found
    results["pass"] = results["keyword_hit_rate"] >= 0.70 and results["entity_found"]

    return results


def run_eval(verbose: bool = True) -> dict:
    print(f"Running evaluation on {len(BENCHMARK)} benchmark queries...\n")
    results = []
    passed = 0

    for item in BENCHMARK:
        print(f"[{item['id']}] {item['query'][:60]}...")
        answer = run_agent(item["query"], verbose=False)
        scores = score_response(answer, item["expected"])

        result = {
            "id": item["id"],
            "query": item["query"],
            "answer": answer,
            "scores": scores,
            "timestamp": datetime.datetime.now().isoformat()
        }
        results.append(result)

        status = "PASS" if scores["pass"] else "FAIL"
        if scores["pass"]:
            passed += 1

        print(f"  Status: {status}")
        print(f"  Keyword hit rate: {scores['keyword_hit_rate']:.0%}")
        if scores["keyword_misses"]:
            print(f"  Missing keywords: {scores['keyword_misses']}")
        print()

    summary = {
        "total": len(BENCHMARK),
        "passed": passed,
        "failed": len(BENCHMARK) - passed,
        "pass_rate": passed / len(BENCHMARK),
        "timestamp": datetime.datetime.now().isoformat(),
        "results": results
    }

    # save results
    output_path = "data/eval_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"{'='*50}")
    print(f"Evaluation complete")
    print(f"  Passed: {passed}/{len(BENCHMARK)} ({summary['pass_rate']:.0%})")
    print(f"  Results saved to {output_path}")

    return summary


if __name__ == "__main__":
    run_eval()