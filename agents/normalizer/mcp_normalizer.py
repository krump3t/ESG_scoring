"""
MCP Normalizer Agent for Bronze to Silver Transformation
Critical Path: Document normalization, chunking, deduplication
"""
from typing import Dict, List, Any, Optional
import logging
import uuid
from datetime import datetime
import re

from iceberg.tables.silver_schema import SilverSchema

logger = logging.getLogger(__name__)


class MCPNormalizerAgent:
    """
    MCP Normalizer Agent for ESG document normalization

    Provides tools for:
    - bronze.read: Read raw documents from bronze layer
    - normalize.chunk: Chunk text into finding-sized segments
    - normalize.deduplicate: Deduplicate findings by hash
    - silver.write: Write normalized findings to silver layer
    """

    def __init__(self) -> None:
        """Initialize MCP Normalizer Agent"""
        self.tools = self._define_tools()
        logger.info(f"Initialized MCP Normalizer Agent with {len(self.tools)} tools")

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define MCP tools for normalizer agent"""
        return [
            {
                "name": "bronze.read",
                "description": "Read raw document from bronze Parquet layer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "org_id": {
                            "type": "string",
                            "description": "Organization identifier"
                        },
                        "year": {
                            "type": "integer",
                            "description": "Reporting year"
                        },
                        "doc_id": {
                            "type": "string",
                            "description": "Document UUID"
                        }
                    },
                    "required": ["org_id", "year", "doc_id"]
                }
            },
            {
                "name": "normalize.chunk",
                "description": "Chunk raw text into finding-sized segments",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Raw text to chunk"
                        },
                        "chunk_size": {
                            "type": "integer",
                            "description": "Target chunk size in characters",
                            "default": 500
                        },
                        "overlap": {
                            "type": "integer",
                            "description": "Overlap between chunks",
                            "default": 50
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "normalize.deduplicate",
                "description": "Deduplicate findings using hash-based matching",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "findings": {
                            "type": "array",
                            "description": "List of findings to deduplicate"
                        }
                    },
                    "required": ["findings"]
                }
            },
            {
                "name": "silver.write",
                "description": "Write normalized findings to silver Iceberg layer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "findings": {
                            "type": "array",
                            "description": "Normalized findings to write"
                        },
                        "merge": {
                            "type": "boolean",
                            "description": "Use MERGE upsert (default true)",
                            "default": True
                        }
                    },
                    "required": ["findings"]
                }
            }
        ]

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name"""
        for tool in self.tools:
            if tool['name'] == tool_name:
                return tool
        return None

    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return [tool['name'] for tool in self.tools]

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Chunk text into segments with overlap

        Args:
            text: Raw text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters

        Returns:
            List of text chunks
        """
        if not text or len(text) == 0:
            return []

        # Split into sentences for better boundaries
        sentences = re.split(r'[.!?]\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Add sentence if it fits
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + ". "
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Handle overlap by taking last N characters
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + sentence + ". "
                else:
                    current_chunk = sentence + ". "

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def extract_findings(self, text: str, org_id: str, year: int,
                        source_doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract findings from text with theme/framework detection

        Args:
            text: Text to extract findings from
            org_id: Organization identifier
            year: Reporting year
            source_doc_id: Source document ID

        Returns:
            List of finding dictionaries
        """
        if source_doc_id is None:
            source_doc_id = str(uuid.uuid4())

        # Chunk text
        chunks = self.chunk_text(text, chunk_size=500, overlap=50)

        findings = []
        for idx, chunk in enumerate(chunks):
            # Skip very short chunks
            if len(chunk) < 20:
                continue

            finding = {
                'finding_id': str(uuid.uuid4()),
                'org_id': org_id,
                'year': year,
                'source_doc_id': source_doc_id,
                'page_number': 0,  # Could be enhanced with page tracking
                'finding_text': chunk,
                'context': '',  # Could add surrounding context
                'theme': self._detect_theme(chunk),
                'framework': self._detect_framework(chunk),
                'metric_type': self._detect_metric_type(chunk),
                'extraction_method': 'chunking',
                'extraction_confidence': 0.8,  # Base confidence
                'extraction_timestamp': datetime.utcnow(),
                'dedup_cluster_id': ''  # For near-duplicate grouping
            }

            findings.append(finding)

        return findings

    def _detect_theme(self, text: str) -> str:
        """Detect ESG theme from text"""
        text_lower = text.lower()

        # Climate/Environmental keywords
        if any(kw in text_lower for kw in [
            'climate', 'emissions', 'carbon', 'ghg', 'net-zero', 'renewable',
            'scope 1', 'scope 2', 'scope 3', 'temperature', 'warming'
        ]):
            return 'Climate'

        # Social keywords
        if any(kw in text_lower for kw in [
            'diversity', 'equity', 'inclusion', 'dei', 'labor', 'human rights',
            'employee', 'community', 'safety', 'health'
        ]):
            return 'Social'

        # Governance keywords
        if any(kw in text_lower for kw in [
            'board', 'governance', 'ethics', 'compliance', 'oversight',
            'risk management', 'audit', 'transparency'
        ]):
            return 'Governance'

        # Environmental (non-climate)
        if any(kw in text_lower for kw in [
            'water', 'waste', 'biodiversity', 'pollution', 'circular',
            'recycling', 'ecosystem'
        ]):
            return 'Environmental'

        return 'Unclassified'

    def _detect_framework(self, text: str) -> str:
        """Detect reporting framework from text"""
        text_lower = text.lower()

        # Framework detection patterns
        frameworks = {
            'SBTi': ['sbti', 'science-based target', 'science based target'],
            'TCFD': ['tcfd', 'task force on climate'],
            'ISSB': ['issb', 'sustainability standards board'],
            'GHG Protocol': ['ghg protocol', 'greenhouse gas protocol'],
            'CSRD': ['csrd', 'corporate sustainability reporting'],
            'ESRS': ['esrs', 'european sustainability reporting'],
            'CDP': ['cdp disclosure', 'carbon disclosure project'],
            'GRI': ['gri standard', 'global reporting initiative'],
            'SASB': ['sasb', 'sustainability accounting standards']
        }

        for framework, patterns in frameworks.items():
            if any(pattern in text_lower for pattern in patterns):
                return framework

        return ''

    def _detect_metric_type(self, text: str) -> str:
        """Detect metric type from text"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ['target', 'goal', 'commitment', 'by 20']):
            return 'target'
        elif any(kw in text_lower for kw in ['achieved', 'reduced', 'actual', 'reported']):
            return 'actual'
        elif any(kw in text_lower for kw in ['policy', 'procedure', 'governance', 'process']):
            return 'policy'

        return 'general'

    def deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate findings using hash-based matching

        Args:
            findings: List of findings to deduplicate

        Returns:
            Deduplicated list of findings with finding_hash added
        """
        seen_hashes = set()
        deduped = []

        for finding in findings:
            # Calculate hash
            finding_hash = SilverSchema.calculate_finding_hash(
                finding['org_id'],
                finding['finding_text'],
                finding['source_doc_id']
            )

            # Skip if already seen
            if finding_hash in seen_hashes:
                logger.debug(f"Skipping duplicate finding: {finding_hash[:16]}...")
                continue

            # Add hash and keep finding
            finding['finding_hash'] = finding_hash
            seen_hashes.add(finding_hash)
            deduped.append(finding)

        logger.info(f"Deduplicated {len(findings)} -> {len(deduped)} findings")
        return deduped

    def normalize_document(self, bronze_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Complete normalization pipeline: bronze -> silver

        Args:
            bronze_data: Bronze layer document data

        Returns:
            List of normalized findings ready for silver layer
        """
        org_id = bronze_data['org_id']
        year = bronze_data['year']
        doc_id = bronze_data['doc_id']
        raw_text = bronze_data['raw_text']

        logger.info(f"Normalizing document: {org_id}/{year}/{doc_id}")

        # Extract findings
        findings = self.extract_findings(raw_text, org_id, year, doc_id)
        logger.info(f"Extracted {len(findings)} raw findings")

        # Deduplicate
        deduped_findings = self.deduplicate_findings(findings)
        logger.info(f"After deduplication: {len(deduped_findings)} findings")

        # Validate against silver schema
        valid_findings = []
        for finding in deduped_findings:
            if SilverSchema.validate_finding(finding):
                valid_findings.append(finding)
            else:
                logger.warning(f"Invalid finding skipped: {finding.get('finding_id')}")

        logger.info(f"Validated {len(valid_findings)} findings for silver layer")

        return valid_findings
