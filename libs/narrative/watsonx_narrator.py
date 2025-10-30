"""
WatsonX Narrator - LLM-Powered ESG Narrative Generation

Generates natural language ESG maturity assessments using watsonx.ai LLMs
with full determinism, caching, and evidence grounding.

Author: SCA v13.8-MEA
Protocol: Authentic computation, zero mocks, fail-closed validation
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import WatsonX client (will use existing caching infrastructure)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from libs.wx.wx_client import WatsonxClient


class WatsonxNarrator:
    """
    LLM-powered narrative generation for ESG maturity assessments.

    Uses meta-llama/llama-3-70b-instruct with temperature=0.0 for
    deterministic, evidence-grounded narrative generation.
    """

    # Prompt templates
    EXECUTIVE_SUMMARY_PROMPT = """You are an ESG analyst writing an executive summary for a sustainability maturity assessment.

COMPANY: {company_name} ({year})
OVERALL MATURITY: Average Stage {overall_stage:.1f}

THEME SCORES:
{theme_scores_text}

INSTRUCTIONS:
1. Write a 2-3 paragraph executive summary (150-200 words total)
2. Paragraph 1: Overall positioning and maturity level interpretation
3. Paragraph 2: Highlight top 3 strengths (themes at Stage 3+)
4. Paragraph 3: Identify key gaps and improvement areas (themes at Stage ≤1)
5. Use evidence-based language but be concise
6. DO NOT fabricate specific metrics or numbers not provided above
7. DO NOT include JSON, markdown headers, or metadata in your response

OUTPUT FORMAT:
Return ONLY the narrative text as plain paragraphs. No formatting, no headers, just the prose.
"""

    THEME_ANALYSIS_PROMPT = """You are an ESG analyst writing a detailed assessment for the ESG theme: {theme_name} ({theme_code}).

SCORE: Stage {stage} (confidence: {confidence:.2f})
STAGE DESCRIPTOR: {descriptor}

EVIDENCE FROM SUSTAINABILITY REPORT:
{evidence_text}

RUBRIC CONTEXT:
Stage {stage}: {descriptor}

INSTRUCTIONS:
1. Write exactly 3-4 sentences explaining WHY this Stage {stage} score is appropriate
2. Reference specific evidence by page number (e.g., "Page 12 demonstrates...")
3. Explain how the evidence aligns with the rubric criteria for Stage {stage}
4. If confidence < 0.7, briefly acknowledge data quality limitations
5. Use precise, evidence-grounded language
6. DO NOT fabricate evidence, page numbers, or metrics not provided above
7. DO NOT include markdown formatting or headers

OUTPUT FORMAT:
Return ONLY the narrative paragraph as plain text. No bullet points, no headers, just prose.
"""

    def __init__(self, offline_replay: bool = False, rubric_path: Optional[str] = None):
        """
        Initialize narrator with WatsonX client.

        Args:
            offline_replay: If True, enforce cache-only mode (fail on cache miss)
            rubric_path: Path to maturity rubric JSON (optional, for context)
        """
        self.wx_client = WatsonxClient(offline_replay=offline_replay)
        self.offline_replay = offline_replay
        self.rubric = None

        if rubric_path and Path(rubric_path).exists():
            self.rubric = json.loads(Path(rubric_path).read_text(encoding="utf-8"))

    def generate_executive_summary(
        self,
        company_name: str,
        year: int,
        theme_scores: List[Dict[str, Any]],
        doc_id: str
    ) -> str:
        """
        Generate executive summary using LLM.

        Args:
            company_name: Company name
            year: Fiscal year
            theme_scores: List of theme score dicts with keys: theme_code, stage, confidence
            doc_id: Document ID for cache keying

        Returns:
            2-3 paragraph executive summary (plain text)
        """
        # Calculate overall average stage
        stages = [s.get("stage", 0) for s in theme_scores if s.get("stage") is not None]
        overall_stage = sum(stages) / len(stages) if stages else 0

        # Format theme scores for prompt
        theme_scores_text = "\n".join([
            f"- {s.get('theme_code', 'UNKNOWN')}: Stage {s.get('stage', 0)} (confidence: {s.get('confidence', 0):.2f})"
            for s in theme_scores
        ])

        # Build prompt
        prompt = self.EXECUTIVE_SUMMARY_PROMPT.format(
            company_name=company_name,
            year=year,
            overall_stage=overall_stage,
            theme_scores_text=theme_scores_text
        )

        # Generate via LLM (uses caching internally)
        narrative = self.wx_client.edit_text(
            prompt=prompt,
            content="",  # No content to edit, pure generation
            model_id="meta-llama/llama-3-70b-instruct",
            temperature=0.0,  # Deterministic
            max_new_tokens=512,  # ~200 words
            doc_id=doc_id
        )

        return narrative.strip()

    def generate_theme_analysis(
        self,
        theme_code: str,
        theme_name: str,
        stage: int,
        confidence: float,
        descriptor: str,
        evidence: List[Dict[str, Any]],
        doc_id: str
    ) -> str:
        """
        Generate narrative analysis for a single theme.

        Args:
            theme_code: Theme code (e.g., "TSP")
            theme_name: Full theme name
            stage: Maturity stage (0-4)
            confidence: Confidence score (0-1)
            descriptor: Rubric descriptor for this stage
            evidence: List of evidence dicts with keys: page_no, text_30w, hash_sha256
            doc_id: Document ID for cache keying

        Returns:
            3-4 sentence narrative analysis (plain text)
        """
        # Format evidence for prompt
        if not evidence:
            evidence_text = "(No evidence provided)"
        else:
            evidence_text = "\n".join([
                f"- Page {ev.get('page_no', '?')}: \"{ev.get('text_30w', ev.get('text', ''))[:100]}...\" "
                f"(hash: {ev.get('hash_sha256', 'N/A')[:8]})"
                for ev in evidence[:5]  # Limit to 5 evidence snippets to avoid token overflow
            ])

        # Build prompt
        prompt = self.THEME_ANALYSIS_PROMPT.format(
            theme_name=theme_name,
            theme_code=theme_code,
            stage=stage,
            confidence=confidence,
            descriptor=descriptor,
            evidence_text=evidence_text
        )

        # Generate via LLM
        narrative = self.wx_client.edit_text(
            prompt=prompt,
            content="",
            model_id="meta-llama/llama-3-70b-instruct",
            temperature=0.0,
            max_new_tokens=256,  # ~100 words for 3-4 sentences
            doc_id=f"{doc_id}_{theme_code}"
        )

        return narrative.strip()

    def generate_full_report(
        self,
        company_name: str,
        year: int,
        scoring_response: Dict[str, Any],
        rubric: Dict[str, Any],
        doc_id: str
    ) -> Dict[str, str]:
        """
        Generate complete LLM-powered narrative report.

        Args:
            company_name: Company name
            year: Fiscal year
            scoring_response: Full scoring response JSON with theme_scores and evidence_records
            rubric: ESG maturity rubric with theme descriptors
            doc_id: Document ID for cache keying

        Returns:
            Dict with keys:
                - executive_summary: str
                - theme_analyses: Dict[theme_code, str]
        """
        theme_scores = scoring_response.get("theme_scores", [])
        evidence_records = scoring_response.get("evidence_records", [])

        # Generate executive summary
        executive_summary = self.generate_executive_summary(
            company_name=company_name,
            year=year,
            theme_scores=theme_scores,
            doc_id=doc_id
        )

        # Generate theme analyses
        theme_analyses = {}
        for theme_score in theme_scores:
            theme_code = theme_score.get("theme_code")
            if not theme_code:
                continue

            # Find rubric info for this theme
            theme_rubric = next(
                (t for t in rubric.get("themes", []) if t.get("code") == theme_code),
                {}
            )
            theme_name = theme_rubric.get("name", theme_code)

            # Find evidence for this theme
            theme_evidence = [
                ev for ev in evidence_records
                if ev.get("theme_code") == theme_code
            ]

            # Get stage descriptor from rubric
            stage = theme_score.get("stage", 0)
            stages_dict = theme_rubric.get("stages", {})
            descriptor = stages_dict.get(str(stage), {}).get("descriptor", "No descriptor available")

            # Generate narrative
            analysis = self.generate_theme_analysis(
                theme_code=theme_code,
                theme_name=theme_name,
                stage=stage,
                confidence=theme_score.get("confidence", 0.0),
                descriptor=descriptor,
                evidence=theme_evidence,
                doc_id=doc_id
            )

            theme_analyses[theme_code] = analysis

        return {
            "executive_summary": executive_summary,
            "theme_analyses": theme_analyses
        }
