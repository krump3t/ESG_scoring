"""
CDP Climate Change Cached Data Extractor

Extracts findings from cached CDP Climate Change disclosure data

Input: JSON file with CDP API response structure
Output: Normalized findings list (compatible with evidence_aggregator)

Author: SCA v13.8-MEA
Task: DEMO-001 Multi-Source E2E Demo
Protocol: No mocks, reads real cached API data
"""
import json
from typing import List, Dict, Any
from pathlib import Path


class CDPExtractor:
    """
    Extract findings from cached CDP Climate Change data

    Extracts from key sections:
    - Governance (board oversight, management responsibility)
    - Strategy (climate targets, transition plan)
    - GHG Emissions (Scope 1/2/3, verification)
    - Renewable Energy
    - Risks & Opportunities
    """

    def __init__(self) -> None:
        """Initialize CDP extractor"""
        self.name = "CDPExtractor"

    def extract(self, cache_path: str) -> Dict[str, Any]:
        """
        Extract findings from cached CDP JSON

        Args:
            cache_path: Path to cached CDP JSON file

        Returns:
            {
                "findings": List[Dict],  # Normalized finding records
                "metadata": Dict  # Source metadata
            }
        """
        # Read cached data
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        findings = []
        finding_id_counter = 1

        # Extract governance findings
        findings.extend(self._extract_governance(data, finding_id_counter))
        finding_id_counter += len(findings)

        # Extract strategy findings (targets)
        findings.extend(self._extract_strategy(data, finding_id_counter))
        finding_id_counter = len(findings) + 1

        # Extract GHG emissions findings
        findings.extend(self._extract_ghg_emissions(data, finding_id_counter))
        finding_id_counter = len(findings) + 1

        # Extract renewable energy findings
        findings.extend(self._extract_renewable_energy(data, finding_id_counter))
        finding_id_counter = len(findings) + 1

        # Extract risks/opportunities findings
        findings.extend(self._extract_risks(data, finding_id_counter))

        return {
            "findings": findings,
            "metadata": {
                "source": "CDP Climate Change",
                "company": data.get("company_name"),
                "year": data.get("year"),
                "cdp_score": data.get("cdp_score"),
                "sha256": data.get("metadata", {}).get("sha256")
            }
        }

    def _extract_governance(self, data: Dict, start_id: int) -> List[Dict[str, Any]]:
        """Extract governance findings from CDP data"""
        findings = []
        gov = data.get("governance", {})

        if gov.get("board_oversight"):
            findings.append({
                "finding_id": f"cdp-{start_id:03d}",
                "text": gov["board_oversight"],
                "theme": "Governance",
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(gov["board_oversight"]),
                "entities": ["Board of Directors", "Audit and Finance Committee"],
                "frameworks": ["CDP"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        if gov.get("management_responsibility"):
            findings.append({
                "finding_id": f"cdp-{start_id + len(findings):03d}",
                "text": gov["management_responsibility"],
                "theme": "Governance",
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(gov["management_responsibility"]),
                "entities": ["VP Environment", "Senior Leadership"],
                "frameworks": ["CDP"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        return findings

    def _extract_strategy(self, data: Dict, start_id: int) -> List[Dict[str, Any]]:
        """Extract strategy findings (climate targets)"""
        findings = []
        strategy = data.get("strategy", {})
        targets = strategy.get("climate_targets", [])

        for idx, target in enumerate(targets):
            target_text = (
                f"Target: {target.get('target', 'Unknown')}. "
                f"Target year: {target.get('target_year', 'Not specified')}. "
                f"Baseline year: {target.get('baseline_year', 'Not specified')}. "
                f"Coverage: {target.get('coverage', 'Not specified')}. "
                f"Status: {target.get('status', 'Unknown')}."
            )

            if target.get("sbti_validated"):
                target_text += " SBTi validated."

            findings.append({
                "finding_id": f"cdp-{start_id + idx:03d}",
                "text": target_text,
                "theme": "TSP",  # Target Setting & Planning
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(target_text),
                "entities": [str(target.get("target_year")), target.get("coverage", "")],
                "frameworks": ["SBTi"] if target.get("sbti_validated") else ["CDP"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        # Add transition plan text
        if strategy.get("transition_plan"):
            findings.append({
                "finding_id": f"cdp-{start_id + len(findings):03d}",
                "text": strategy["transition_plan"],
                "theme": "TSP",
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(strategy["transition_plan"]),
                "entities": ["renewable energy", "carbon removal", "energy efficiency"],
                "frameworks": ["CDP"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        return findings

    def _extract_ghg_emissions(self, data: Dict, start_id: int) -> List[Dict[str, Any]]:
        """Extract GHG emissions findings"""
        findings = []
        ghg = data.get("ghg_emissions", {})

        if ghg:
            # Build emissions summary text
            emissions_text = (
                f"GHG Emissions Inventory (Year: {ghg.get('year', 'Unknown')}). "
                f"Scope 1: {ghg.get('scope_1_tco2e', 0):,} tCO2e. "
                f"Scope 2 (market-based): {ghg.get('scope_2_tco2e_market', 0):,} tCO2e. "
                f"Scope 3: {ghg.get('scope_3_tco2e', 0):,} tCO2e. "
                f"Total: {ghg.get('total_tco2e', 0):,} tCO2e. "
                f"Methodology: {ghg.get('methodology', 'Not specified')}. "
                f"Verification: {ghg.get('verification', 'None')}."
            )

            findings.append({
                "finding_id": f"cdp-{start_id:03d}",
                "text": emissions_text,
                "theme": "GHG",
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(emissions_text),
                "entities": [
                    f"{ghg.get('total_tco2e', 0):,} tCO2e",
                    "GHG Protocol",
                    "Third-party verification"
                ],
                "frameworks": ["GHG Protocol"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        return findings

    def _extract_renewable_energy(self, data: Dict, start_id: int) -> List[Dict[str, Any]]:
        """Extract renewable energy findings"""
        findings = []
        renewable = data.get("renewable_energy", {})

        if renewable:
            renewable_text = (
                f"Renewable Energy: {renewable.get('renewable_percentage', 0)}% of total consumption. "
                f"Total consumption: {renewable.get('total_consumption_mwh', 0):,} MWh. "
                f"Renewable: {renewable.get('renewable_mwh', 0):,} MWh. "
                f"Sources: Solar ({renewable.get('sources', {}).get('solar', 0):,} MWh), "
                f"Wind ({renewable.get('sources', {}).get('wind', 0):,} MWh). "
                f"{renewable.get('supplier_renewable_commitment', '')}."
            )

            findings.append({
                "finding_id": f"cdp-{start_id:03d}",
                "text": renewable_text,
                "theme": "EI",  # Energy Intelligence
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(renewable_text),
                "entities": [f"{renewable.get('renewable_percentage', 0)}%", "RE100"],
                "frameworks": ["CDP", "RE100"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        return findings

    def _extract_risks(self, data: Dict, start_id: int) -> List[Dict[str, Any]]:
        """Extract climate risks and opportunities"""
        findings = []
        risks_opps = data.get("risks_opportunities", {})

        # Physical risks
        for idx, risk in enumerate(risks_opps.get("physical_risks", [])):
            risk_text = (
                f"Physical Risk ({risk.get('type', 'Unknown')}): {risk.get('description', '')}. "
                f"Impact: {risk.get('impact', 'Unknown')}. "
                f"Likelihood: {risk.get('likelihood', 'Unknown')}. "
                f"Time horizon: {risk.get('time_horizon', 'Unknown')}."
            )

            findings.append({
                "finding_id": f"cdp-{start_id + len(findings):03d}",
                "text": risk_text,
                "theme": "RMM",  # Risk Management & Mitigation
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(risk_text),
                "entities": [risk.get("type", ""), risk.get("time_horizon", "")],
                "frameworks": ["TCFD", "CDP"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        # Transition risks (similar structure)
        for idx, risk in enumerate(risks_opps.get("transition_risks", [])):
            risk_text = (
                f"Transition Risk ({risk.get('type', 'Unknown')}): {risk.get('description', '')}. "
                f"Impact: {risk.get('impact', 'Unknown')}. "
                f"Likelihood: {risk.get('likelihood', 'Unknown')}."
            )

            findings.append({
                "finding_id": f"cdp-{start_id + len(findings):03d}",
                "text": risk_text,
                "theme": "RMM",
                "source_id": "cdp_climate_change",
                "source_type": "CDP",
                "doc_id": f"cdp-{data.get('company_name', 'unknown').lower().replace(' ', '-')}-{data.get('year')}",
                "page_no": None,
                "char_start": 0,
                "char_end": len(risk_text),
                "entities": [risk.get("type", "")],
                "frameworks": ["TCFD", "CDP"],
                "org_id": data.get("company_name"),
                "year": data.get("year")
            })

        return findings
