"""Local-LLM business-directory scraper.

`lead_gen_pipeline` extracts structured business data from web pages and Chamber of
Commerce member directories. Single pages are parsed deterministically by
:class:`~lead_gen_pipeline.scraper.HTMLScraper`; directory navigation and listing
extraction are driven by a local LLM (Qwen2-7B via llama.cpp) through a pluggable
:class:`~lead_gen_pipeline.llm_processor.LLMBackend`.
"""

__version__ = "1.0.0"
