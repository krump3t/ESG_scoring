# ESG Maturity Scoring Rubric v3.0 (Aligned with ESG Doc)

> Purpose: Direct alignment with the ESG Doc’s structured maturity scoring system, providing theme‑specific stage descriptors, evidence criteria, and automation points for MCP‑Iceberg integration.

**Scale:** 0–4 per theme
**Themes (7):**

1. Target Setting & Planning (TSP)
2. Operational Structure & Processes (OSP)
3. Data Maturity (DM)
4. GHG Accounting (GHG)
5. Reporting & Disclosure (RD)
6. Energy Intelligence (EI)
7. Risk Management & Mitigation (RMM)

---

## 1) Target Setting & Planning (TSP)

**Intent:** Evaluate ambition, structure, and credibility of targets.

| Stage | Descriptor                                                                                                                                           | Evidence examples                                       |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **0** | No targets or vague qualitative commitments.                                                                                                         | Generic CSR statements.                                 |
| **1** | Short‑term qualitative or partial quantitative targets.                                                                                              | Reduction claims without clear scope/baseline.          |
| **2** | Time‑bound quantitative targets with disclosed baseline year, scope coverage, and KPIs.                                                              | Target table; baseline definition.                      |
| **3** | Science‑based methodology or SBTi submission; scenario modeling present but not financially linked; supplier engagement.                             | SBTi pending; scenarios; supplier data efforts.         |
| **4** | Validated science‑based targets (SBTi or equivalent); financial integration (CAPEX/OPEX linkage); scenario planning embedded in enterprise strategy. | SBTi approval; financial modeling; executive oversight. |

---

## 2) Operational Structure & Processes (OSP)

**Intent:** Evaluate ESG integration within operations and governance.

| Stage | Descriptor                                                                                                                | Evidence examples                                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **0** | No ESG governance or process.                                                                                             | None.                                                  |
| **1** | Ad‑hoc initiatives; isolated ownership.                                                                                   | Named owner or department references.                  |
| **2** | Formalized processes, roles, and documented policies.                                                                     | Process maps; KPI templates.                           |
| **3** | Cross‑functional collaboration with clear KPIs, accountability, and oversight.                                            | ESG steering committee minutes; quarterly KPI reviews. |
| **4** | Fully embedded ESG management system with internal audit, continuous improvement, and integrated financial risk controls. | Audit report; control register.                        |

---

## 3) Data Maturity (DM)

**Intent:** Assess data quality, automation, and system architecture.

| Stage | Descriptor                                                                                                                               | Evidence examples                                        |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **0** | Manual, inconsistent data entry; no governance.                                                                                          | Spreadsheet exports.                                     |
| **1** | Structured but manual data collection; limited validation.                                                                               | Collection forms; basic validation notes.                |
| **2** | Partially automated collection; standardized formats; QA protocols.                                                                      | ETL diagrams; validation logs.                           |
| **3** | Centralized database with integration across functions; periodic audits; supplier data exchange.                                         | Unified platform documentation; supplier data workflows. |
| **4** | Automated pipelines with real‑time validation, lineage tracking, and integrated reporting systems (e.g., Iceberg, Parquet architecture). | System architecture; API/ETL logs.                       |

---

## 4) GHG Accounting (GHG)

**Intent:** Evaluate completeness, accuracy, and assurance of emissions data.

| Stage | Descriptor                                                                                                  | Evidence examples                                       |
| ----- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **0** | No emissions accounting.                                                                                    | N/A                                                     |
| **1** | Partial Scope 1/2 estimates without methodology.                                                            | Estimate table.                                         |
| **2** | Scope 1/2 complete; partial Scope 3 with standard factors; recalculation policy.                            | Methodology note; base year documentation.              |
| **3** | Comprehensive Scope 1/2/3 with data improvement plans, supplier engagement, and limited assurance.          | Supplier engagement report; assurance letter (limited). |
| **4** | Full third‑party reasonable assurance; GHG Protocol compliance; uncertainty analysis; auditor verification. | Verifier statement; audit summary.                      |

---

## 5) Reporting & Disclosure (RD)

**Intent:** Measure transparency, alignment, and timeliness of ESG reporting.

| Stage | Descriptor                                                                                              | Evidence examples                  |
| ----- | ------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **0** | No formal ESG reporting.                                                                                | Brochure text.                     |
| **1** | CSR/GRI index partial coverage; narrative only.                                                         | GRI mapping.                       |
| **2** | ISSB/TCFD‑aligned narrative; annual updates.                                                            | TCFD section.                      |
| **3** | Cross‑framework KPI alignment; dual materiality; investor reporting consistency.                        | CSRD/ESRS mapping; KPI dashboards. |
| **4** | External assurance; digital tagging (XBRL/ESRS); integrated financial filing; near‑real‑time reporting. | Assurance letter; tagging export.  |

---

## 6) Energy Intelligence (EI)

**Intent:** Evaluate monitoring, optimization, and forecasting of energy and resource use.

| Stage | Descriptor                                                                                             | Evidence examples                   |
| ----- | ------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| **0** | No tracking beyond invoices.                                                                           | Utility bills.                      |
| **1** | Basic metering and periodic reviews.                                                                   | Meter inventory.                    |
| **2** | Systematic KPIs and improvement projects tracked.                                                      | KPI dashboard; project list.        |
| **3** | Automated monitoring and analytics; predictive maintenance; integration with ESG data.                 | EMS screenshots; alerts.            |
| **4** | AI/ML forecasting; optimization across assets; cost‑benefit analysis tied to decarbonization strategy. | Forecast graphs; optimization logs. |

---

## 7) Risk Management & Mitigation (RMM)

**Intent:** Evaluate climate/ESG risk identification and mitigation integration.

| Stage | Descriptor                                                                                                       | Evidence examples                          |
| ----- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **0** | No risk framework or ESG integration.                                                                            | N/A                                        |
| **1** | Qualitative risk statements without quantification.                                                              | Narrative.                                 |
| **2** | Defined risk taxonomy; periodic assessments; basic mitigation plans.                                             | Risk matrix; mitigation summary.           |
| **3** | Quantified risk assessments (transition/physical); scenario testing; integrated into planning.                   | Scenario analysis; governance charter.     |
| **4** | Enterprise risk integrated with financial modeling; insured/uninsured analysis; public disclosure per ISSB/CSRD. | Annual report section; disclosure summary. |

---

## Evidence Model (for MCP‑Iceberg)

* Each score references evidence spans (document + page + text extract + hash).
* `gold.esg_evidence`: `evidence_id`, `org_id`, `year`, `theme`, `doc_id`, `page_no`, `span_start`, `span_end`, `extract_30w`, `hash_sha256`, `snapshot_id`.
* Scores join on `evidence_ids[]` + `snapshot_id` + `doc_manifest_uri` (AstraDB pointer).
* Freshness rule: evidence >24 months reduces confidence by 0.1.
* Explainability Agent ranks top‑10 excerpts by relevance × recency.

---

## Overall Maturity Grade

| Average Score | Maturity Level |
| ------------- | -------------- |
| 0–0.9         | Nascent        |
| 1.0–1.9       | Emerging       |
| 2.0–2.9       | Established    |
| 3.0–3.5       | Advanced       |
| 3.6–4.0       | Leading        |

---

**Version:** 3.0
**Alignment:** Mirrors stages, language, and evidence thresholds from the ESG Doc while maintaining machine‑readable structure for Iceberg and MCP use.
