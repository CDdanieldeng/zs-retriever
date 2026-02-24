#!/usr/bin/env python3
"""Quick test for rerank API. Run from backend/: python scripts/test_rerank.py"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend / "src"))

from app.services.providers.registry import get_rerank_provider


def main():
    docs = [
        "文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序",
        "量子计算是计算科学的一个前沿领域",
        "预训练语言模型的发展给文本排序模型带来了新的进展",
    ]
    query = "什么是文本排序模型"

    print("Testing rerank provider...")
    provider = get_rerank_provider()
    print(f"Provider: {type(provider).__name__}")

    results = provider.rerank(query, docs, top_n=2)
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  index={r.index}, score={r.score:.4f}, text={r.text[:30]}...")
    print("OK")


if __name__ == "__main__":
    main()
