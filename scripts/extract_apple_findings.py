"""
Extract ESG Findings from Apple 2022 Environmental Progress Report

Uses the ingestion pipeline to:
1. Extract full text from PDF via pdf_extractor
2. Chunk text into candidate findings (paragraph-level)
3. Filter for substantive ESG disclosures
4. Classify by theme and framework
5. Output findings dataset for scoring

Protocol: SCA v13.8-MEA
Task: 005-microsoft-full-analysis (pivoted to Apple)
"""
import sys
from pathlib import Path
import json
import re
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.crawler.extractors.pdf_extractor import PDFExtractor

# Paths
TASK_DIR = PROJECT_ROOT / "tasks" / "005-microsoft-full-analysis"
ARTIFACTS_DIR = TASK_DIR / "artifacts"
PDF_PATH = PROJECT_ROOT / "data" / "pdf_cache" / "ed9a89cf9feb626c5bb8429f8dddfba6.pdf"


class FindingExtractor:
    """Extract structured findings from raw PDF text"""

    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.theme_keywords = {
            "Climate": ["carbon", "emissions", "ghg", "climate", "decarboniz", "renewable energy", "solar", "wind"],
            "Energy": ["energy", "electricity", "power", "renewable", "efficiency", "consumption"],
            "Operations": ["facility", "operations", "manufacturing", "supply chain", "datacenter", "campus"],
            "Materials": ["recycled", "material", "circular", "product design", "aluminum", "packaging"],
            "Water": ["water", "consumption", "usage", "replenish", "freshwater"],
            "Waste": ["waste", "recycling", "landfill", "circular economy", "reuse"],
            "Governance": ["oversight", "board", "executive", "committee", "governance", "policy"],
            "Risk": ["risk", "scenario", "tcfd", "climate-related financial", "vulnerability"],
            "Disclosure": ["report", "disclosure", "transparency", "cdp", "gri", "sasb", "tcfd"],
            "Social": ["community", "education", "workforce", "diversity", "equity", "inclusion"]
        }

        self.framework_patterns = [
            (r'TCFD|Task Force on Climate', "TCFD"),
            (r'GRI|Global Reporting Initiative', "GRI"),
            (r'SASB', "SASB"),
            (r'CDP', "CDP"),
            (r'SBTi|Science Based Targets', "SBTi"),
            (r'GHG Protocol', "GHG Protocol"),
            (r'RE100', "RE100"),
            (r'ISO 14001', "ISO 14001"),
        ]

    def extract_findings(self, min_findings: int = 50, max_findings: int = 100) -> List[Dict[str, Any]]:
        """
        Extract 50-100 findings from Apple PDF

        Returns:
            List of findings with structure:
            - finding_id: str
            - finding_text: str (≥50 chars)
            - theme: str
            - framework: str | None
            - page: int
            - section: str
        """
        print("=" * 80)
        print("EXTRACTING FINDINGS FROM APPLE 2022 ENVIRONMENTAL PROGRESS REPORT")
        print("=" * 80)

        # Step 1: Extract PDF
        print(f"\n[1/5] Extracting PDF: {PDF_PATH.name}")
        result = self.pdf_extractor.extract(str(PDF_PATH), extract_tables=False, extract_images=False)

        print(f"  Pages: {result['page_count']}")
        print(f"  Text length: {len(result['text']):,} chars")
        print(f"  SHA256: {result['sha256'][:16]}...")

        # Step 2: Chunk into paragraphs
        print(f"\n[2/5] Chunking text into paragraphs...")
        paragraphs = self._chunk_text(result['text'])
        print(f"  Total paragraphs: {len(paragraphs)}")

        # Step 3: Filter for substantive ESG content
        print(f"\n[3/5] Filtering for substantive ESG disclosures...")
        candidates = self._filter_substantive(paragraphs)
        print(f"  Substantive candidates: {len(candidates)}")

        # Step 4: Select top findings (highest ESG relevance)
        print(f"\n[4/5] Selecting top {min_findings}-{max_findings} findings...")
        findings = self._select_top_findings(candidates, min_findings, max_findings)
        print(f"  Selected findings: {len(findings)}")

        # Step 5: Classify themes and frameworks
        print(f"\n[5/5] Classifying themes and frameworks...")
        for finding in findings:
            finding['theme'] = self._classify_theme(finding['text'])
            finding['framework'] = self._detect_framework(finding['text'])

        # Print theme distribution
        theme_counts = {}
        for f in findings:
            theme_counts[f['theme']] = theme_counts.get(f['theme'], 0) + 1

        print(f"\n  Theme distribution:")
        for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
            print(f"    {theme}: {count}")

        return findings

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Chunk text into paragraphs with metadata"""
        # Split on double newlines (paragraph breaks)
        raw_paragraphs = text.split('\n\n')

        paragraphs = []
        for idx, para in enumerate(raw_paragraphs):
            # Clean whitespace
            clean_para = ' '.join(para.split())

            if len(clean_para) >= 50:  # Minimum length threshold
                paragraphs.append({
                    'index': idx,
                    'text': clean_para,
                    'length': len(clean_para)
                })

        return paragraphs

    def _filter_substantive(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter for substantive ESG content"""
        candidates = []

        for para in paragraphs:
            text_lower = para['text'].lower()

            # Skip if too short or too long
            if len(para['text']) < 100 or len(para['text']) > 2000:
                continue

            # Skip if looks like table of contents, headers, footers
            if self._is_boilerplate(para['text']):
                continue

            # Calculate ESG relevance score
            relevance_score = self._calculate_esg_relevance(text_lower)

            if relevance_score > 0:
                para['relevance_score'] = relevance_score
                candidates.append(para)

        # Sort by relevance
        candidates.sort(key=lambda x: x['relevance_score'], reverse=True)

        return candidates

    def _is_boilerplate(self, text: str) -> bool:
        """Check if text is boilerplate (TOC, headers, footers)"""
        boilerplate_patterns = [
            r'^Contents$',
            r'^Page \d+',
            r'^\d+\s*$',
            r'^Environmental Progress Report',
            r'^Apple Inc\.',
            r'^©\s*\d{4}',
        ]

        for pattern in boilerplate_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def _calculate_esg_relevance(self, text_lower: str) -> float:
        """Calculate ESG relevance score (0-10)"""
        score = 0.0

        # Check for theme keywords
        for theme, keywords in self.theme_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    score += 0.5

        # Bonus for quantitative data (metrics)
        if re.search(r'\d+%|\d+\s*(metric tons|MW|GW|gigawatts|megawatts)', text_lower):
            score += 1.0

        # Bonus for policy/commitment language
        policy_terms = ["commit", "target", "goal", "plan", "strateg", "achieve", "reduce"]
        for term in policy_terms:
            if term in text_lower:
                score += 0.5

        return min(score, 10.0)  # Cap at 10

    def _select_top_findings(self, candidates: List[Dict[str, Any]],
                             min_findings: int, max_findings: int) -> List[Dict[str, Any]]:
        """Select top N findings ensuring diversity"""
        # Take top candidates but ensure diversity across document
        # Strategy: Take top 150, then subsample to ensure page distribution

        top_candidates = candidates[:min(150, len(candidates))]

        # Assign estimated page numbers (rough estimate: 3500 chars per page)
        for candidate in top_candidates:
            estimated_page = int(candidate['index'] * 3500 / 405250 * 114) + 1
            candidate['page'] = min(estimated_page, 114)

        # Diverse sampling: ensure at least one finding per 10 pages
        findings = []
        page_buckets = {i: [] for i in range(1, 115, 10)}  # 10-page buckets

        for candidate in top_candidates:
            bucket = (candidate['page'] // 10) * 10 + 1
            if bucket in page_buckets:
                page_buckets[bucket].append(candidate)

        # Take top from each bucket
        for bucket, bucket_candidates in sorted(page_buckets.items()):
            if bucket_candidates:
                # Take top 5-8 from each bucket
                findings.extend(bucket_candidates[:min(8, len(bucket_candidates))])

        # Trim to target range
        findings = findings[:max_findings]

        # Format findings
        formatted_findings = []
        for idx, f in enumerate(findings):
            formatted_findings.append({
                'finding_id': f"apple_2022_{idx+1:03d}",
                'text': f['text'],
                'page': f['page'],
                'section': self._extract_section_name(f['text']),
                'relevance_score': f['relevance_score']
            })

        return formatted_findings

    def _classify_theme(self, text: str) -> str:
        """Classify finding theme"""
        text_lower = text.lower()

        theme_scores = {}
        for theme, keywords in self.theme_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                theme_scores[theme] = score

        if not theme_scores:
            return "General"

        return max(theme_scores, key=theme_scores.get)

    def _detect_framework(self, text: str) -> str:
        """Detect ESG framework mention"""
        for pattern, framework in self.framework_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return framework

        return "Internal"

    def _extract_section_name(self, text: str) -> str:
        """Extract section name (first 3-5 words)"""
        words = text.split()[:5]
        section = ' '.join(words)
        if len(section) > 50:
            section = section[:47] + "..."
        return section

    def save_findings(self, findings: List[Dict[str, Any]]):
        """Save findings to artifacts"""
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

        output = {
            "company": "Apple",
            "year": 2022,
            "report_type": "Environmental Progress Report",
            "extraction_date": datetime.utcnow().isoformat() + "Z",
            "findings_count": len(findings),
            "findings": findings
        }

        output_file = ARTIFACTS_DIR / "apple_2022_full_findings.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n[OK] Findings saved to: {output_file}")
        return output_file


def main():
    """Extract findings from Apple 2022 report"""
    extractor = FindingExtractor()

    # Extract 50-100 findings
    findings = extractor.extract_findings(min_findings=50, max_findings=100)

    # Save to artifacts
    output_file = extractor.save_findings(findings)

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Findings extracted: {len(findings)}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
