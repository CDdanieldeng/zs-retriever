#!/usr/bin/env python3
"""Quick test for embedding API. Run from backend/: python scripts/test_embedding.py"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# Ensure backend/src is on path when run from project root
backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend / "src"))

from app.services.providers.registry import get_embedding_provider


def main():
    texts = ["北京是中国的首都", "上海是经济中心", "测试 embedding API"]
    print("Testing embedding provider...")
    print(f"Input: {texts}")

    provider = get_embedding_provider()
    print(f"Provider: {type(provider).__name__}")
    print(f"Dimension: {provider.dimension}")

    vecs = provider.embed(texts)
    print(f"Output: {len(vecs)} vectors")

    for i, (t, v) in enumerate(zip(texts, vecs)):
        print(f"  [{i}] len={len(v)}, sample={v[:3] if v else []}...")

    print("OK")


if __name__ == "__main__":
    main()
