"""LLM-powered chamber-directory processing.

The :class:`LLMProcessor` turns chamber pages into structured data: it preprocesses HTML
to compact Markdown, prompts a language model for directory links and business listings,
and parses the response with a JSON-repair fallback for malformed output.

The model is reached through a pluggable :class:`LLMBackend`. The default
:class:`LlamaCppBackend` runs Qwen2-7B locally via llama.cpp; tests inject a fake
backend so the whole pipeline can be exercised without the 4 GB model.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import OrderedDict
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urljoin

try:
    from json_repair import repair_json

    JSON_REPAIR_AVAILABLE = True
except ImportError:  # pragma: no cover
    JSON_REPAIR_AVAILABLE = False
    repair_json = None  # type: ignore[assignment]

try:
    import markdownify

    MARKDOWNIFY_AVAILABLE = True
except ImportError:  # pragma: no cover
    markdownify = None  # type: ignore[assignment]
    MARKDOWNIFY_AVAILABLE = False

try:
    from .config import LLMSettings
    from .config import settings as app_settings
    from .utils import logger
except ImportError:  # pragma: no cover
    from lead_gen_pipeline.config import LLMSettings  # type: ignore
    from lead_gen_pipeline.config import settings as app_settings  # type: ignore
    from lead_gen_pipeline.utils import logger  # type: ignore


# Shared output schema. Kept as a superset of what both prompts request so a single
# grammar can constrain either call; unused fields are simply omitted by the model.
_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "navigation_links": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "integer"},
        "business_listings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "website": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "address": {"type": "string"},
                    "industry": {"type": "string"},
                },
            },
        },
        "pagination": {
            "type": "object",
            "properties": {
                "next_page_url": {"type": "string"},
                "has_more": {"type": "boolean"},
            },
        },
        "total_found": {"type": "integer"},
    },
}


@runtime_checkable
class LLMBackend(Protocol):
    """A text-in, text-out language-model backend.

    Implementations are synchronous and may block (the local llama.cpp backend does);
    :class:`LLMProcessor` calls them off the event loop via :func:`asyncio.to_thread`.
    """

    def ensure_ready(self) -> bool:
        """Load any heavy resources. Return True when the backend can generate."""

    def generate(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        """Return the model's completion for ``prompt`` (expected to be JSON)."""


class LlamaCppBackend:
    """Default backend: Qwen2-7B-Instruct (GGUF) via llama.cpp.

    The model is loaded lazily on first use. JSON output is constrained with a grammar
    derived from :data:`_OUTPUT_JSON_SCHEMA`.
    """

    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or app_settings.llm
        self._llm: Any = None
        self._grammar: Any = None
        self._ready = False

    def ensure_ready(self) -> bool:
        if self._ready:
            return True
        try:
            from llama_cpp import Llama
            from llama_cpp.llama_grammar import LlamaGrammar
        except ImportError:
            logger.error(
                "llama-cpp-python not available. Install with "
                "`pip install 'lead-gen-pipeline[llm]'`."
            )
            return False

        model_path = self.settings.MODEL_PATH
        if not model_path.exists():
            logger.error(
                f"Model not found: {model_path}. Run `lead-gen setup-llm` first."
            )
            return False

        logger.info(f"Loading Qwen2 model from {model_path} ...")
        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=self.settings.CONTEXT_SIZE,
            n_threads=None,
            n_gpu_layers=self.settings.N_GPU_LAYERS,
            verbose=False,
            use_mmap=True,
            seed=self.settings.SEED,
        )
        self._grammar = LlamaGrammar.from_json_schema(json.dumps(_OUTPUT_JSON_SCHEMA))
        self._ready = True
        logger.success("Qwen2 model loaded.")
        return True

    def unload(self) -> None:
        """Release the loaded model so its memory can be reclaimed."""
        self._llm = None
        self._grammar = None
        self._ready = False

    def generate(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        if not self._ready:
            raise RuntimeError("Backend not ready; call ensure_ready() first.")
        call_kwargs: dict[str, Any] = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "grammar": self._grammar,
            "stop": ["</s>", "\n\n\n"],
        }
        try:
            response = self._llm(
                prompt, response_format={"type": "json_object"}, **call_kwargs
            )
        except TypeError:
            # Older llama-cpp builds do not accept response_format.
            response = self._llm(prompt, **call_kwargs)
        return str(response["choices"][0]["text"]).strip()


class LLMProcessor:
    """Drives an :class:`LLMBackend` to extract structured chamber-directory data."""

    def __init__(
        self,
        backend: LLMBackend | None = None,
        settings: LLMSettings | None = None,
    ) -> None:
        self.settings = settings or app_settings.llm
        self.backend: LLMBackend = backend or LlamaCppBackend(self.settings)
        self.model_loaded = False
        self._html_cache: OrderedDict[str, str] = OrderedDict()

    async def initialize(self) -> bool:
        """Ensure the backend is ready (loading the model off the event loop)."""
        if self.model_loaded:
            return True
        self.model_loaded = await asyncio.to_thread(self.backend.ensure_ready)
        if not self.model_loaded:
            logger.error("LLM backend failed to initialize.")
        return self.model_loaded

    def _robust_json_parse(self, raw_output: str) -> Any | None:
        """Parse model output as JSON, repairing malformed output when possible."""
        if not raw_output or not raw_output.strip():
            return None

        output = raw_output.strip()
        for fence in ("```json", "```"):
            if output.startswith(fence):
                output = output[len(fence) :]
                break
        if output.endswith("```"):
            output = output[:-3]
        output = output.strip()

        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")

        if JSON_REPAIR_AVAILABLE and repair_json is not None:
            try:
                repaired = repair_json(output, return_objects=True)
            except Exception as repair_error:
                logger.error(f"JSON repair failed: {repair_error}")
                return None
            if isinstance(repaired, (dict, list)) and repaired:
                logger.success("JSON repair succeeded.")
                return repaired
            logger.error("JSON repair returned empty data.")
            return None

        logger.error("json-repair not available; cannot recover malformed output.")
        return None

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown to reduce token count for the model."""
        if not MARKDOWNIFY_AVAILABLE or markdownify is None:
            from bs4 import BeautifulSoup

            return BeautifulSoup(html_content, "html.parser").get_text(
                separator="\n", strip=True
            )

        markdown = markdownify.markdownify(
            html_content, heading_style="ATX", bullets="-"
        )
        return re.sub(r"\n\s*\n\s*\n", "\n\n", markdown).strip()

    def _preprocess_chamber_page(self, html_content: str) -> str:
        """Convert and truncate a page to fit the model context, with an LRU cache."""
        cache_key = hashlib.md5(html_content.encode()).hexdigest()
        cached = self._html_cache.get(cache_key)
        if cached is not None:
            self._html_cache.move_to_end(cache_key)
            return cached

        markdown = self._html_to_markdown(html_content)
        max_chars = self.settings.CONTEXT_SIZE * 3
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Content truncated]"

        if len(self._html_cache) >= self.settings.HTML_CACHE_SIZE:
            self._html_cache.popitem(last=False)
        self._html_cache[cache_key] = markdown
        return markdown

    def _create_directory_navigation_prompt(self, page_content: str) -> str:
        return f"""\
Analyze this Chamber of Commerce page and find business directory links.

Respond with valid JSON only - no markdown, no explanations.

Page content:
{page_content}

Look for: "Members", "Directory", "Businesses", "Member Directory", etc.

JSON format:
{{
  "navigation_links": ["url1", "url2"],
  "confidence": 85
}}

Empty array if no directory links found."""

    def _create_business_extraction_prompt(self, page_content: str) -> str:
        return f"""Extract business data from this chamber directory page.

JSON only - no extra text.

Page content:
{page_content}

JSON format:
{{
  "business_listings": [
    {{
      "name": "Business Name",
      "website": "http://example.com",
      "phone": "555-1234",
      "email": "contact@example.com",
      "address": "123 Main St, City, State",
      "industry": "Business Category"
    }}
  ],
  "pagination": {{
    "next_page_url": null,
    "has_more": false
  }},
  "total_found": 0
}}

Use null for missing fields. Extract all businesses found."""

    async def _generate(self, prompt: str) -> str:
        return await asyncio.to_thread(
            self.backend.generate,
            prompt,
            max_tokens=self.settings.MAX_TOKENS,
            temperature=self.settings.TEMPERATURE,
        )

    async def find_directory_links(self, html_content: str, url: str) -> list[str]:
        """Return absolute URLs of business-directory pages found on a chamber page."""
        if not self.model_loaded and not await self.initialize():
            return []

        try:
            prompt = self._create_directory_navigation_prompt(
                self._preprocess_chamber_page(html_content)
            )
            logger.info(f"Analyzing chamber page: {url}")
            result = self._robust_json_parse(await self._generate(prompt))
        except Exception as e:
            logger.error(f"Error finding directory links for {url}: {e}")
            return []

        if not isinstance(result, dict):
            logger.error("LLM response was not a JSON object for directory links.")
            return []

        links: list[str] = []
        for link in result.get("navigation_links", []) or []:
            if not isinstance(link, str) or not link.strip():
                continue
            links.append(link if link.startswith("http") else urljoin(url, link))
        logger.success(f"Found {len(links)} directory links on {url}")
        return links

    async def extract_business_listings(
        self, html_content: str, url: str
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return cleaned business records and the next-page URL (if any)."""
        if not self.model_loaded and not await self.initialize():
            return [], None

        try:
            prompt = self._create_business_extraction_prompt(
                self._preprocess_chamber_page(html_content)
            )
            logger.info(f"Extracting businesses from: {url}")
            result = self._robust_json_parse(await self._generate(prompt))
        except Exception as e:
            logger.error(f"Error extracting businesses from {url}: {e}")
            return [], None

        if not isinstance(result, dict):
            logger.error("LLM response was not a JSON object for business listings.")
            return [], None

        pagination = result.get("pagination") or {}
        next_page_url = (
            pagination.get("next_page_url") if isinstance(pagination, dict) else None
        )
        if next_page_url and not str(next_page_url).startswith("http"):
            next_page_url = urljoin(url, str(next_page_url))

        cleaned: list[dict[str, Any]] = []
        for business in result.get("business_listings", []) or []:
            if not isinstance(business, dict):
                continue
            record = {
                field: (str(business.get(field) or "").strip() or None)
                for field in (
                    "name",
                    "website",
                    "phone",
                    "email",
                    "address",
                    "industry",
                )
            }
            record["source_url"] = url
            if record["name"] or record["website"]:
                cleaned.append(record)

        logger.success(f"Extracted {len(cleaned)} businesses from {url}")
        return cleaned, next_page_url

    async def close(self) -> None:
        """Release the backend's model and clear the preprocessing cache."""
        if isinstance(self.backend, LlamaCppBackend):
            self.backend.unload()
        self.model_loaded = False
        self._html_cache.clear()
        logger.info("LLM processor cleaned up.")


_llm_processor_singleton: LLMProcessor | None = None


def get_llm_processor() -> LLMProcessor:
    """Return the process-wide :class:`LLMProcessor`, creating it on first use."""
    global _llm_processor_singleton
    if _llm_processor_singleton is None:
        _llm_processor_singleton = LLMProcessor()
    return _llm_processor_singleton


def create_llm_processor(backend: LLMBackend | None = None) -> LLMProcessor:
    """Create a fresh :class:`LLMProcessor`, optionally with a custom backend."""
    return LLMProcessor(backend=backend)
