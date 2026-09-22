"""Live-model test, excluded from the default run.

Marked ``live_llm`` and skipped unless the Qwen2-7B GGUF model is present. Run it with:

    pytest -m live_llm
"""

import pytest

from lead_gen_pipeline.config import settings
from lead_gen_pipeline.llm_processor import LLMProcessor

SAMPLE_DIRECTORY = """
<html><body>
  <div class="member"><h3>Acme Robotics</h3>
    <a href="https://acme.example">acme.example</a>
    <span>(303) 556-0123</span></div>
  <div class="member"><h3>Beta Consulting</h3>
    <a href="https://beta.example">beta.example</a></div>
</body></html>
"""


@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_model_extracts_business_listings():
    if not settings.llm.MODEL_PATH.exists():
        pytest.skip(f"Qwen2 model not found at {settings.llm.MODEL_PATH}")

    processor = LLMProcessor()
    assert await processor.initialize(), "model failed to load"
    try:
        businesses, _ = await processor.extract_business_listings(
            SAMPLE_DIRECTORY, "https://chamber.example/members"
        )
    finally:
        await processor.close()

    assert isinstance(businesses, list)
    names = {b.get("name", "").lower() for b in businesses}
    assert any("acme" in n for n in names)
