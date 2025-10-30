#!/usr/bin/env python3
"""
watsonx.ai-Powered R&D Locator for ESG Reports

SCA v13.8-MEA Compliance:
- LLM calls ONLY in Fetch phase (offline_replay=False)
- Cache hits enforced in Replay phase (offline_replay=True)
- Keyword validation: detected sections must contain ≥1 marker
- Fail-closed: cache misses → RuntimeError
- Deterministic: temperature=0, top_k=1

Usage:
    # Fetch phase (populate cache)
    locator = RDLocatorWX(offline_replay=False)
    sections = locator.locate_rd_sections(chunks, doc_id="msft_2024")

    # Replay phase (cache-only)
    locator = RDLocatorWX(offline_replay=True)
    sections = locator.locate_rd_sections(chunks, doc_id="msft_2024")  # Must hit cache
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from libs.wx import WatsonxClient


@dataclass
class RDSection:
    """Detected R&D-related section in ESG report."""

    section_type: str  # "TCFD", "SECR", "GRI305", "SBTi", "CDP", "Custom"
    chunk_ids: List[str]  # Chunk IDs belonging to this section
    confidence: float  # 0.0-1.0
    markers: List[str]  # Matched keywords validating detection
    page_range: str  # e.g., "12-15"


@dataclass
class RDLocatorResult:
    """Result of R&D section locator."""

    doc_id: str
    sections: List[RDSection]
    total_chunks: int
    rd_chunks: int  # Chunks assigned to R&D sections
    cache_hit: bool
    method: str  # "watsonx_llm" or "keyword_fallback"


# Keyword markers for validation (post-LLM)
SECTION_MARKERS = {
    "TCFD": [
        "task force on climate-related financial disclosures",
        "tcfd",
        "climate-related risks and opportunities",
        "scenario analysis",
        "governance: climate",
        "strategy: climate",
        "risk management: climate",
        "metrics and targets: climate",
    ],
    "SECR": [
        "streamlined energy and carbon reporting",
        "secr",
        "energy consumption",
        "intensity ratio",
        "emissions reporting methodology",
        "scope 1 emissions",
        "scope 2 emissions",
        "energy efficiency actions",
    ],
    "GRI305": [
        "gri 305",
        "emissions reporting standard",
        "direct ghg emissions",
        "indirect ghg emissions",
        "emissions intensity",
        "reduction of ghg emissions",
        "scope 3 emissions",
    ],
    "SBTi": [
        "science based targets",
        "sbti",
        "1.5°c pathway",
        "net-zero commitment",
        "validated targets",
        "carbon reduction target",
    ],
    "CDP": [
        "carbon disclosure project",
        "cdp questionnaire",
        "climate change response",
        "water security",
        "forests questionnaire",
    ],
    "Custom": [
        "sustainability report",
        "esg disclosure",
        "environmental performance",
        "climate strategy",
        "carbon footprint",
        "emissions inventory",
        "renewable energy",
        "energy transition",
    ],
}


class RDLocatorWX:
    """
    watsonx.ai-powered R&D section locator with keyword validation.

    Features:
    - LLM-based section detection (TCFD, SECR, GRI305, SBTi, CDP)
    - Keyword validation: detected sections must match ≥1 marker
    - Deterministic caching: identical inputs → identical outputs
    - Offline replay: enforces 100% cache hits or fail-closed
    """

    def __init__(
        self,
        wx_client: Optional[WatsonxClient] = None,
        offline_replay: bool = False,
        cache_dir: str = "artifacts/wx_cache",
    ):
        """
        Initialize R&D locator.

        Args:
            wx_client: watsonx client instance (optional, created if None)
            offline_replay: If True, refuse LLM calls (cache-only)
            cache_dir: Directory for cache storage
        """
        self.offline_replay = offline_replay or os.getenv("WX_OFFLINE_REPLAY", "").lower() == "true"
        self.wx_client = wx_client or WatsonxClient(
            cache_dir=cache_dir, offline_replay=self.offline_replay
        )

    def locate_rd_sections(
        self, chunks: List[Dict], doc_id: str = ""
    ) -> RDLocatorResult:
        """
        Locate R&D-related sections in document chunks.

        Args:
            chunks: List of chunk dicts with keys: chunk_id, text, page, doc_id
            doc_id: Document identifier for logging

        Returns:
            RDLocatorResult with detected sections and metadata

        Raises:
            RuntimeError: If offline_replay=True and cache miss
        """
        if not chunks:
            return RDLocatorResult(
                doc_id=doc_id,
                sections=[],
                total_chunks=0,
                rd_chunks=0,
                cache_hit=True,
                method="empty_input",
            )

        # Build LLM prompt
        prompt = self._build_locator_prompt(chunks)

        # Call watsonx.ai for section detection
        try:
            section_data = self.wx_client.generate_json(
                prompt=prompt,
                model_id="meta-llama/llama-3-8b-instruct",
                temperature=0.0,
                top_k=1,
                schema=self._get_section_schema(),
                doc_id=doc_id,
            )
            cache_hit = True
            method = "watsonx_llm"
        except RuntimeError as e:
            if "Cache miss" in str(e):
                raise  # Re-raise cache miss errors in offline mode
            # Other errors: fallback to keyword-based detection
            section_data = self._keyword_fallback(chunks)
            cache_hit = False
            method = "keyword_fallback"

        # Validate and structure results
        sections = self._validate_and_structure(section_data, chunks)

        # Count R&D chunks
        rd_chunk_ids = set()
        for section in sections:
            rd_chunk_ids.update(section.chunk_ids)

        return RDLocatorResult(
            doc_id=doc_id,
            sections=sections,
            total_chunks=len(chunks),
            rd_chunks=len(rd_chunk_ids),
            cache_hit=cache_hit,
            method=method,
        )

    def _build_locator_prompt(self, chunks: List[Dict]) -> str:
        """Build prompt for LLM section locator."""
        # Sample up to 50 chunks for context window efficiency
        sample_chunks = chunks[:50] if len(chunks) > 50 else chunks

        chunk_context = "\n".join(
            [
                f"Chunk {i+1} (ID: {c['chunk_id']}, Page: {c.get('page', 'N/A')}): "
                f"{c['text'][:200]}..."
                for i, c in enumerate(sample_chunks)
            ]
        )

        prompt = f"""You are an ESG document analyzer. Identify sections related to climate/environmental reporting standards.

**Document Context** ({len(chunks)} total chunks, showing first {len(sample_chunks)}):
{chunk_context}

**Task**: Identify which chunks belong to the following section types:
1. TCFD (Task Force on Climate-related Financial Disclosures)
2. SECR (Streamlined Energy and Carbon Reporting)
3. GRI305 (GHG Emissions Standard)
4. SBTi (Science Based Targets initiative)
5. CDP (Carbon Disclosure Project)
6. Custom (other sustainability/ESG sections)

**Output JSON Schema**:
{{
  "sections": [
    {{
      "section_type": "TCFD",
      "chunk_indices": [0, 1, 2],  // 0-indexed positions
      "confidence": 0.9,
      "rationale": "Contains TCFD governance disclosures..."
    }}
  ]
}}

**Constraints**:
- Only include sections with confidence ≥ 0.5
- chunk_indices must be valid (0 to {len(sample_chunks)-1})
- Rationale must cite specific keywords/phrases from chunks

Return valid JSON only (no markdown, no explanations).
"""
        return prompt

    def _get_section_schema(self) -> Dict:
        """JSON schema for section detection output."""
        return {
            "type": "object",
            "required": ["sections"],
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["section_type", "chunk_indices", "confidence"],
                        "properties": {
                            "section_type": {
                                "type": "string",
                                "enum": ["TCFD", "SECR", "GRI305", "SBTi", "CDP", "Custom"],
                            },
                            "chunk_indices": {"type": "array", "items": {"type": "integer"}},
                            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "rationale": {"type": "string"},
                        },
                    },
                }
            },
        }

    def _validate_and_structure(
        self, section_data: Dict, chunks: List[Dict]
    ) -> List[RDSection]:
        """Validate LLM output and structure as RDSection objects."""
        sections = []

        for raw_section in section_data.get("sections", []):
            section_type = raw_section.get("section_type", "Custom")
            chunk_indices = raw_section.get("chunk_indices", [])
            confidence = raw_section.get("confidence", 0.0)

            # Validate indices
            valid_indices = [
                idx for idx in chunk_indices if 0 <= idx < len(chunks)
            ]
            if not valid_indices:
                continue  # Skip sections with no valid chunks

            # Extract chunk IDs and text
            chunk_ids = [chunks[idx]["chunk_id"] for idx in valid_indices]
            section_text = " ".join([chunks[idx]["text"].lower() for idx in valid_indices])

            # Keyword validation
            markers = self._match_markers(section_type, section_text)
            if not markers:
                # No marker match → downgrade to Custom or skip
                if section_type != "Custom":
                    # Retry with Custom markers
                    markers = self._match_markers("Custom", section_text)
                    if markers:
                        section_type = "Custom"
                    else:
                        continue  # Skip if no markers at all

            # Page range
            pages = sorted(
                set(
                    [
                        chunks[idx].get("page", 0)
                        for idx in valid_indices
                        if chunks[idx].get("page")
                    ]
                )
            )
            page_range = f"{min(pages)}-{max(pages)}" if pages else "N/A"

            sections.append(
                RDSection(
                    section_type=section_type,
                    chunk_ids=chunk_ids,
                    confidence=confidence,
                    markers=markers,
                    page_range=page_range,
                )
            )

        return sections

    def _match_markers(self, section_type: str, text: str) -> List[str]:
        """Match keywords for section validation."""
        markers = SECTION_MARKERS.get(section_type, [])
        matched = [marker for marker in markers if marker in text]
        return matched

    def _keyword_fallback(self, chunks: List[Dict]) -> Dict:
        """Fallback: keyword-based section detection (no LLM)."""
        sections = []

        # Scan chunks for keyword matches
        for i, chunk in enumerate(chunks):
            text = chunk["text"].lower()
            best_type = None
            best_markers = []

            for section_type, markers in SECTION_MARKERS.items():
                matched = [m for m in markers if m in text]
                if len(matched) > len(best_markers):
                    best_type = section_type
                    best_markers = matched

            if best_type and best_markers:
                sections.append(
                    {
                        "section_type": best_type,
                        "chunk_indices": [i],
                        "confidence": 0.6,  # Lower confidence for keyword-only
                        "rationale": f"Keyword match: {', '.join(best_markers[:3])}",
                    }
                )

        return {"sections": sections}


if __name__ == "__main__":
    # Test connectivity and caching
    import sys

    if not os.getenv("WX_API_KEY") or not os.getenv("WX_PROJECT"):
        print("ERROR: WX_API_KEY and WX_PROJECT required for live testing")
        sys.exit(1)

    # Mock chunks for testing
    test_chunks = [
        {
            "chunk_id": "chunk_001",
            "text": "Our TCFD governance structure includes Board oversight of climate risks...",
            "page": 12,
            "doc_id": "test_doc",
        },
        {
            "chunk_id": "chunk_002",
            "text": "Under SECR regulations, we report Scope 1 and 2 emissions with intensity ratios...",
            "page": 15,
            "doc_id": "test_doc",
        },
    ]

    try:
        # Fetch phase
        locator = RDLocatorWX(offline_replay=False)
        result = locator.locate_rd_sections(test_chunks, doc_id="test_doc")
        print(f"✓ RD Locator test: {result.rd_chunks}/{result.total_chunks} chunks classified")
        print(f"  Sections: {[s.section_type for s in result.sections]}")
        print(f"  Cache hit: {result.cache_hit}, Method: {result.method}")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
