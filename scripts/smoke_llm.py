#!/usr/bin/env python3
"""Smoke-test the local Qwen2-7B model on a sample chamber page.

Requires the GGUF model (run ``lead-gen setup-llm``) and the ``llm`` extra
(``pip install 'lead-gen-pipeline[llm]'``). This is a manual check, not part of the
default test suite.

Usage:
    python scripts/smoke_llm.py
"""

import asyncio

from lead_gen_pipeline.llm_processor import LLMProcessor

SAMPLE_PAGE = """
<html><body>
  <h1>Springfield Chamber of Commerce</h1>
  <nav>
    <a href="/member-directory">Member Directory</a>
    <a href="/about">About</a>
  </nav>
</body></html>
"""


async def main() -> int:
    processor = LLMProcessor()
    if not await processor.initialize():
        print(
            "Model not available. Run `lead-gen setup-llm` and install the llm extra."
        )
        return 1

    links = await processor.find_directory_links(SAMPLE_PAGE, "https://chamber.example")
    print(f"Directory links found: {links}")
    await processor.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
