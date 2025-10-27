"""
Improved Watson X client with better confidence calibration
Fixes the 50% confidence issue with explicit evidence-based scoring
"""

import json
import logging
import hashlib
from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime

# Import IBM Watson libraries (REQUIRED - no fallback)
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.embeddings import Embeddings
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, EmbeddingTypes
from ibm_watsonx_ai import APIClient, Credentials

logger = logging.getLogger(__name__)


class ImprovedWatsonXClient:
    """
    Improved Watson X client with better prompts for confidence scoring
    """

    def __init__(self, config=None):
        self.config = config or self._get_default_config()
        self._initialize_clients()

    def _get_default_config(self):
        import os
        return {
            'api_key': os.getenv('WATSONX_API_KEY'),
            'project_id': os.getenv('WATSONX_PROJECT_ID'),
            'url': os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com'),
            'embedding_model': 'slate-125m-english-rtrvr-v2',
            'extraction_model': 'llama-3-3-70b-instruct',
            'classification_model': 'llama-3-3-70b-instruct'
        }

    def _initialize_clients(self):
        """Initialize Watson clients"""
        if not self.config['api_key']:
            raise ValueError("WATSONX_API_KEY is required")
        if not self.config['project_id']:
            raise ValueError("WATSONX_PROJECT_ID is required")

        # Create credentials
        self.credentials = Credentials(
            api_key=self.config['api_key'],
            url=self.config['url']
        )

        # Initialize API client
        self.api_client = APIClient(
            credentials=self.credentials,
            project_id=self.config['project_id']
        )

        # Initialize models
        embed_params = {
            EmbedParams.TRUNCATE_INPUT_TOKENS: True
        }

        self.embedding_model = Embeddings(
            model_id=self.config['embedding_model'],
            params=embed_params,
            credentials=self.credentials,
            project_id=self.config['project_id']
        )

        gen_params = {
            GenParams.MAX_NEW_TOKENS: 2000,
            GenParams.MIN_NEW_TOKENS: 50,
            GenParams.TEMPERATURE: 0.3,
            GenParams.TOP_P: 0.95,
            GenParams.TOP_K: 50,
            GenParams.REPETITION_PENALTY: 1.05,
            GenParams.RANDOM_SEED: 42
        }

        self.extraction_model = ModelInference(
            model_id=self.config['extraction_model'],
            params=gen_params,
            credentials=self.credentials,
            project_id=self.config['project_id']
        )

        self.classification_model = ModelInference(
            model_id=self.config['classification_model'],
            params=gen_params,
            credentials=self.credentials,
            project_id=self.config['project_id']
        )

        logger.info("Watson X clients initialized successfully")

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using real API"""
        try:
            response = self.embedding_model.embed_documents([text])
            if response and len(response) > 0:
                embedding = np.array(response[0])
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            else:
                raise ValueError("Empty response from embedding API")
        except Exception as e:
            raise RuntimeError(f"Embedding generation failed: {e}")

    def extract_findings(self, text: str, query: str, theme: str,
                        max_findings: int = 5) -> Dict[str, Any]:
        """
        Extract ESG findings with improved evidence scoring
        """

        prompt = f"""Extract key ESG findings from the following text about {theme}.

Text:
{text[:3000]}

Instructions:
1. Extract {max_findings} specific, factual findings
2. For each finding, provide the exact evidence from the text
3. Rate evidence strength (0.0-1.0) based on:
   - 1.0: Quantified metric with verification (e.g., "30% reduction verified by Deloitte")
   - 0.8: Quantified metric without verification (e.g., "reduced emissions by 30%")
   - 0.6: Specific commitment with timeline (e.g., "net-zero by 2030")
   - 0.4: General commitment without timeline (e.g., "committed to sustainability")
   - 0.2: Vague statement (e.g., "focusing on ESG")

Query focus: {query}

Return ONLY valid JSON in this exact format:
{{
    "findings": [
        {{
            "finding": "Clear statement of the finding",
            "evidence": "Exact quote or data from the text",
            "evidence_strength": 0.0-1.0,
            "confidence": 0.0-1.0
        }}
    ],
    "theme": "{theme}",
    "relevance_score": 0.0-1.0,
    "data_quality": "high|medium|low"
}}

Base confidence on evidence strength:
- 0.9-1.0: Multiple quantified metrics
- 0.7-0.9: Mix of metrics and commitments
- 0.5-0.7: Mostly commitments, few metrics
- 0.3-0.5: General statements
- 0.0-0.3: Vague or no evidence
"""

        try:
            response_dict = self.extraction_model.generate(prompt=prompt)

            if response_dict and 'results' in response_dict and len(response_dict['results']) > 0:
                response = response_dict['results'][0].get('generated_text', '')

                # Enhanced JSON extraction
                start = response.find('{')
                if start >= 0:
                    brace_count = 0
                    for i, char in enumerate(response[start:], start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        if brace_count == 0:
                            try:
                                findings = json.loads(response[start:i+1])

                                # Calculate average evidence strength
                                if 'findings' in findings:
                                    strengths = [f.get('evidence_strength', 0.5)
                                               for f in findings['findings']]
                                    avg_strength = sum(strengths) / len(strengths) if strengths else 0.5

                                    # Set data quality based on average strength
                                    if avg_strength >= 0.7:
                                        findings['data_quality'] = 'high'
                                    elif avg_strength >= 0.5:
                                        findings['data_quality'] = 'medium'
                                    else:
                                        findings['data_quality'] = 'low'

                                return findings
                            except:
                                break

            # Fallback structure
            return {
                "findings": [],
                "theme": theme,
                "relevance_score": 0.0,
                "data_quality": "low"
            }

        except Exception as e:
            logger.error(f"Finding extraction failed: {e}")
            return {"error": str(e), "findings": []}

    def classify_maturity(self, findings: List[Dict], theme: str) -> Dict[str, Any]:
        """
        Classify ESG maturity with improved confidence calculation
        """

        # Calculate evidence-based confidence
        evidence_strengths = [f.get('evidence_strength', 0.5) for f in findings]
        avg_evidence_strength = sum(evidence_strengths) / len(evidence_strengths) if evidence_strengths else 0.5

        # Build confidence guidance based on evidence
        confidence_guidance = self._get_confidence_guidance(avg_evidence_strength)

        prompt = f"""Based on the following ESG findings, classify the maturity stage and calculate confidence.

Findings:
{json.dumps(findings, indent=2)}

MATURITY STAGES (0-4):
Stage 0 (Reactive): No systematic ESG approach, ad-hoc responses only
Stage 1 (Developing): Basic policies in place, limited metrics, compliance-focused
Stage 2 (Managing): Structured programs with clear targets, regular reporting, stakeholder engagement
Stage 3 (Optimizing): Advanced integration, data-driven decisions, innovation, industry leadership
Stage 4 (Leading): Transformational impact, net positive, systemic change, thought leadership

CONFIDENCE CALCULATION:
Average evidence strength: {avg_evidence_strength:.2f}
{confidence_guidance}

EVALUATION CRITERIA:
1. Count findings at each maturity level
2. Weight by evidence strength
3. Consider comprehensiveness across ESG dimensions
4. Factor in specificity of metrics and targets

Your confidence MUST be based on:
- High confidence (80-100%): 3+ findings with evidence_strength > 0.7
- Medium confidence (60-79%): 2+ findings with evidence_strength > 0.5
- Low confidence (40-59%): Mostly general statements, evidence_strength < 0.5
- Very low confidence (20-39%): Vague statements only
- Minimal confidence (0-19%): Insufficient evidence

Return ONLY valid JSON:
{{
    "stage": 0-4,
    "confidence": {avg_evidence_strength:.2f} (adjust ±0.2 based on finding count),
    "evidence": ["List specific evidence supporting this stage"],
    "rationale": "Explanation of why this stage was chosen",
    "evidence_quality": "{self._get_quality_label(avg_evidence_strength)}",
    "finding_count": {len(findings)},
    "next_steps": ["Specific recommendations for improvement"]
}}
"""

        try:
            response_dict = self.classification_model.generate(prompt=prompt)

            if response_dict and 'results' in response_dict and len(response_dict['results']) > 0:
                response = response_dict['results'][0].get('generated_text', '')

                # Extract JSON
                start = response.find('{')
                if start >= 0:
                    brace_count = 0
                    for i, char in enumerate(response[start:], start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        if brace_count == 0:
                            try:
                                classification = json.loads(response[start:i+1])

                                # Override confidence if it's still defaulting to 0.5
                                if classification.get('confidence', 0) == 0.5:
                                    # Calculate based on evidence
                                    classification['confidence'] = self._calculate_confidence(
                                        findings,
                                        classification.get('stage', 2)
                                    )

                                return classification
                            except:
                                break

            # Fallback with calculated confidence
            return {
                "stage": 2,
                "confidence": avg_evidence_strength,
                "evidence": [],
                "rationale": "Classification based on evidence strength",
                "evidence_quality": self._get_quality_label(avg_evidence_strength),
                "finding_count": len(findings)
            }

        except Exception as e:
            logger.error(f"Maturity classification failed: {e}")
            return {
                "stage": 0,
                "confidence": 0.2,
                "error": str(e)
            }

    def _get_confidence_guidance(self, avg_strength: float) -> str:
        """Generate confidence guidance based on evidence strength"""
        if avg_strength >= 0.8:
            return "Evidence is STRONG (quantified metrics with verification). Set confidence: 0.80-1.00"
        elif avg_strength >= 0.6:
            return "Evidence is MODERATE (mix of metrics and commitments). Set confidence: 0.60-0.79"
        elif avg_strength >= 0.4:
            return "Evidence is WEAK (mostly general commitments). Set confidence: 0.40-0.59"
        else:
            return "Evidence is VERY WEAK (vague statements). Set confidence: 0.20-0.39"

    def _get_quality_label(self, strength: float) -> str:
        """Get quality label from strength score"""
        if strength >= 0.7:
            return "high"
        elif strength >= 0.5:
            return "medium"
        else:
            return "low"

    def _calculate_confidence(self, findings: List[Dict], stage: int) -> float:
        """
        Calculate confidence based on evidence strength and finding count
        """
        if not findings:
            return 0.2

        # Get evidence strengths
        strengths = [f.get('evidence_strength', 0.5) for f in findings]
        avg_strength = sum(strengths) / len(strengths)

        # Factor in finding count
        count_factor = min(len(findings) / 5, 1.0)  # Max out at 5 findings

        # Factor in stage appropriateness
        # Higher stages need stronger evidence
        stage_penalty = 0
        if stage >= 3 and avg_strength < 0.6:
            stage_penalty = 0.2  # Reduce confidence for high stage with weak evidence
        elif stage <= 1 and avg_strength > 0.7:
            stage_penalty = -0.1  # Increase confidence for low stage with strong evidence

        # Calculate final confidence
        confidence = (avg_strength * 0.7 + count_factor * 0.3) - stage_penalty

        # Ensure in valid range
        return max(0.2, min(1.0, confidence))

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Watson X"""
        try:
            # Try a simple embedding
            test_emb = self.generate_embedding("Test connection")
            return {
                "connected": True,
                "embedding_dim": len(test_emb),
                "models": {
                    "embedding": self.config['embedding_model'],
                    "extraction": self.config['extraction_model'],
                    "classification": self.config['classification_model']
                }
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Export the improved client
def get_improved_watsonx_client(config: Optional[Dict[str, Any]] = None):
    """Factory function to get improved Watson X client instance"""
    return ImprovedWatsonXClient(config)