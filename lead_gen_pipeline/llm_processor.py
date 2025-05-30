# lead_gen_pipeline/llm_processor.py
# LLM-powered chamber directory processing

import os
import json
import re
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
import tempfile
import hashlib

# CRITICAL: Import json-repair for handling malformed LLM JSON
try:
    from json_repair import repair_json
    JSON_REPAIR_AVAILABLE = True
except ImportError:
    JSON_REPAIR_AVAILABLE = False
    repair_json = None

try:
    from llama_cpp import Llama
    from llama_cpp.llama_grammar import LlamaGrammar
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    Llama = None
    LlamaGrammar = None
    LLAMA_CPP_AVAILABLE = False

try:
    import markdownify
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    markdownify = None
    MARKDOWNIFY_AVAILABLE = False

try:
    from .utils import logger
    from .config import settings
except ImportError:
    from lead_gen_pipeline.utils import logger
    from lead_gen_pipeline.config import settings

class LLMProcessor:
    """Handles Qwen2-7B integration for chamber directory parsing."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._get_default_model_path()
        self.llm: Optional[Llama] = None
        self.model_loaded = False
        self._context_size = 32768
        self._max_tokens = 4096
        self._temperature = 0.0  # Deterministic output for JSON
        
        self._json_grammar = None
        self._html_cache: Dict[str, str] = {}  # LRU cache for processed HTML
        self._cache_max_size = 100
        
        logger.info(f"LLMProcessor initialized with model path: {self.model_path}")
    
    def _get_default_model_path(self) -> str:
        """Check common model locations."""
        paths = [
            "./models/qwen2-7b-instruct-q4_k_m.gguf",
            "/models/qwen2-7b-instruct-q4_k_m.gguf",
            os.path.expanduser("~/.cache/huggingface/hub/qwen2-7b-instruct-q4_k_m.gguf"),
            os.path.expanduser("~/models/qwen2-7b-instruct-q4_k_m.gguf")
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        
        logger.warning("Qwen2 model not found in common locations")
        return "./models/qwen2-7b-instruct-q4_k_m.gguf"
    
    def _robust_json_parse(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """Parse LLM output with json-repair fallback for malformed JSON."""
        if not raw_output or not raw_output.strip():
            return None
        
        # Clean markdown artifacts
        output = raw_output.strip()
        if output.startswith('```json'):
            output = output[7:]
        if output.startswith('```'):
            output = output[3:]
        if output.endswith('```'):
            output = output[:-3]
        output = output.strip()
        
        # Try standard parsing first
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            
            # Fallback to repair
            if JSON_REPAIR_AVAILABLE and repair_json:
                try:
                    logger.info("Attempting JSON repair")
                    repaired = repair_json(output, return_objects=True)
                    
                    if repaired and isinstance(repaired, (dict, list)):
                        logger.success("JSON repair successful")
                        return repaired
                    else:
                        logger.error("JSON repair returned empty data")
                        return None
                        
                except Exception as repair_error:
                    logger.error(f"JSON repair failed: {repair_error}")
                    return None
            else:
                logger.error("json-repair not available")
                return None
    
    async def initialize(self) -> bool:
        """Initialize the LLM model."""
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama-cpp-python not available. Install with: pip install llama-cpp-python")
            return False
        
        if self.model_loaded:
            return True
            
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return False
            
            logger.info("Loading Qwen2 Instruct 7B model...")
            
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self._context_size,
                n_threads=os.cpu_count() or 4,
                n_gpu_layers=-1,  # Use all available GPU layers
                verbose=False,
                use_mmap=True,
                use_mlock=True,
                seed=42
            )
            
            # JSON schema for structured output
            json_schema = '''
            {
                "type": "object",
                "properties": {
                    "navigation_links": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
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
                                "industry": {"type": "string"}
                            }
                        }
                    },
                    "pagination": {
                        "type": "object",
                        "properties": {
                            "next_page_url": {"type": "string"},
                            "has_more": {"type": "boolean"}
                        }
                    }
                }
            }
            '''
            
            self._json_grammar = LlamaGrammar.from_json_schema(json_schema)
            
            self.model_loaded = True
            logger.success("Qwen2 model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return False
    
    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown for token efficiency."""
        if not MARKDOWNIFY_AVAILABLE:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        
        markdown = markdownify.markdownify(
            html_content,
            heading_style="ATX",
            bullets="-",
            strong_tag="**",
            emphasis_tag="*"
        )
        
        # Clean excessive whitespace
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        return markdown.strip()
    
    def _preprocess_chamber_page(self, html_content: str, url: str) -> str:
        """Preprocess chamber page HTML for LLM consumption."""
        cache_key = hashlib.md5(html_content.encode()).hexdigest()
        
        if cache_key in self._html_cache:
            return self._html_cache[cache_key]
        
        markdown = self._html_to_markdown(html_content)
        
        # Truncate if exceeds context window
        max_chars = self._context_size * 3
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Content truncated]"
        
        # LRU cache management
        if len(self._html_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._html_cache))
            del self._html_cache[oldest_key]
        
        self._html_cache[cache_key] = markdown
        return markdown
    
    def _create_directory_navigation_prompt(self, page_content: str, url: str) -> str:
        # After much iteration, this prompt structure works best for chamber sites
        return f"""Analyze this Chamber of Commerce page and find business directory links.

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
    
    def _create_business_extraction_prompt(self, page_content: str, url: str) -> str:
        # Simplified after testing - direct instructions work better than roleplay
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

    async def find_directory_links(self, html_content: str, url: str) -> List[str]:
        """Find navigation links to chamber business directories."""
        if not self.model_loaded:
            await self.initialize()
        
        if not self.llm:
            logger.error("LLM not initialized")
            return []
        
        try:
            processed_content = self._preprocess_chamber_page(html_content, url)
            prompt = self._create_directory_navigation_prompt(processed_content, url)
            
            logger.info(f"Analyzing chamber page: {url}")
            
            # Try Qwen2 JSON mode if supported
            try:
                response = self.llm(
                    prompt,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    grammar=self._json_grammar,
                    stop=["</s>", "\n\n\n"],
                    response_format={"type": "json_object"}
                )
            except TypeError:
                # Fallback without response_format
                response = self.llm(
                    prompt,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    grammar=self._json_grammar,
                    stop=["</s>", "\n\n\n"]
                )
            
            result_text = response['choices'][0]['text'].strip()
            
            # Use robust JSON parsing with repair fallback
            result = self._robust_json_parse(result_text)
            if result:
                navigation_links = result.get('navigation_links', [])
                
                # Convert relative URLs to absolute
                absolute_links = []
                for link in navigation_links:
                    if link.startswith('http'):
                        absolute_links.append(link)
                    else:
                        absolute_url = urljoin(url, link)
                        absolute_links.append(absolute_url)
                
                logger.success(f"Found {len(absolute_links)} directory links")
                return absolute_links
                
            else:
                logger.error("Failed to parse LLM response")
                return []
                
        except Exception as e:
            logger.error(f"Error finding directory links: {e}")
            return []
    
    async def extract_business_listings(self, html_content: str, url: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Extract business listings from chamber directory pages."""
        if not self.model_loaded:
            await self.initialize()
        
        if not self.llm:
            logger.error("LLM not initialized")
            return [], None
        
        try:
            processed_content = self._preprocess_chamber_page(html_content, url)
            prompt = self._create_business_extraction_prompt(processed_content, url)
            
            logger.info(f"Extracting businesses from: {url}")
            
            # Try to use Qwen2's JSON mode if available
            try:
                response = self.llm(
                    prompt,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    grammar=self._json_grammar,
                    stop=["</s>", "\n\n\n"],
                    response_format={"type": "json_object"}  # Qwen2 JSON mode
                )
            except TypeError:
                # Fallback if response_format not supported
                response = self.llm(
                    prompt,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    grammar=self._json_grammar,
                    stop=["</s>", "\n\n\n"]
                )
            
            result_text = response['choices'][0]['text'].strip()
            
            # Use robust JSON parsing with repair fallback
            result = self._robust_json_parse(result_text)
            if result:
                business_listings = result.get('business_listings', [])
                
                # Handle pagination
                pagination = result.get('pagination', {})
                next_page_url = pagination.get('next_page_url')
                if next_page_url and not next_page_url.startswith('http'):
                    next_page_url = urljoin(url, next_page_url)
                
                # Clean business data
                cleaned_businesses = []
                for business in business_listings:
                    cleaned_business = {
                        'name': business.get('name', '').strip() or None,
                        'website': business.get('website', '').strip() or None,
                        'phone': business.get('phone', '').strip() or None,
                        'email': business.get('email', '').strip() or None,
                        'address': business.get('address', '').strip() or None,
                        'industry': business.get('industry', '').strip() or None,
                        'source_url': url
                    }
                    
                    if cleaned_business['name'] or cleaned_business['website']:
                        cleaned_businesses.append(cleaned_business)
                
                logger.success(f"Extracted {len(cleaned_businesses)} businesses")
                return cleaned_businesses, next_page_url
                
            else:
                logger.error("Failed to parse LLM response")
                return [], None
                
        except Exception as e:
            logger.error(f"Error extracting business listings: {e}")
            return [], None
    
    async def close(self):
        """Clean up model resources."""
        if hasattr(self, 'llm') and self.llm:
            self.llm = None
        self.model_loaded = False
        self._html_cache.clear()
        logger.info("LLM processor cleaned up")


# Factory function - simpler than singleton pattern
def create_llm_processor() -> LLMProcessor:
    """Create new LLM processor instance."""
    return LLMProcessor()
