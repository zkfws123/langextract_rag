"""Quick verification for ZiWei extraction_class stability.

Runs a tiny extraction with the domain prompt/examples and prints:
- distinct extraction_class values
- any bad cases where extraction_class leaked a field name (e.g. 'extraction_text')

Note: This script calls the configured LLM endpoint via langextract.
"""

from __future__ import annotations

import os
from collections import Counter


def main() -> int:
    # Reduce noisy logs unless user wants them.
    os.environ.setdefault("EXTRACTION_QUIET", "1")

    from src.parsers.knowledge_extractor import KnowledgeExtractor
    from src.parsers.relation_extractor import RelationExtractor

    # Mixed snippet: 星曜 + 四化 + 宫位关系 + 案例/技法
    # Keep it short to make debug runs fast.
    text = (
        "# 星曜与四化\n\n"
        "紫微星为帝星，天府星为财库星。\n"
        "禄主缘起，忌主阻滞。\n\n"
        "# 宫位关系\n\n"
        "命宫对宫为迁移宫，三合方为财帛宫与官禄宫。\n\n"
        "# 案例：婚姻分析\n\n"
        "夫妻宫有生年忌，主感情不顺，但也寓意命主必定有婚姻。\n"
        "来因宫在子女宫，以子女为媒介促成婚姻。\n"
        "技法：用‘媒介’与‘串联’看宫位如何推动事件发展。\n"
    )

    exts = KnowledgeExtractor(doc_id="dbg", doc_title="dbg").extract_from_text(text, max_length=5000)

    classes = [e.extraction_class for e in exts]
    counts = Counter(classes)

    bad_values = {"extraction_text", "extraction_class", "char_interval", "attributes"}
    bad = [e for e in exts if (str(e.extraction_class).strip() in bad_values)]

    print(f"extractions_count={len(exts)}")
    print("classes_distinct=", sorted(counts.keys()))
    print("classes_counts=", dict(counts))
    print(f"bad_class_count={len(bad)}")
    if bad:
        for i, e in enumerate(bad[:10], 1):
            print(f"  [bad#{i}] class={e.extraction_class!r} text={str(e.extraction_text)[:80]!r}")

    # Stage-2: relation extraction
    print("\n--- relation_extraction ---")
    try:
        rext = RelationExtractor(chunk_size=20)
        triples = rext.extract_relations(extractions=exts, source_text=text)
        print(f"relations_count={len(triples)}")
        rel_types = Counter(t.relation for t in triples)
        print("relation_types=", dict(rel_types))

        # show a few
        for i, t in enumerate(triples[:10], 1):
            md = t.metadata or {}
            reason = md.get("reason", "")
            print(f"  [R{i}] {t.subject_id} -[{t.relation}]-> {t.object_id} reason={reason!r}")
    except Exception as e:
        # Keep debug output short but actionable.
        print(f"relation_extraction_error={type(e).__name__}: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
