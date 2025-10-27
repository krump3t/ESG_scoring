# ESG Maturity Rubric — Implementation-Ready Specification (v1.0)

> Source: Consolidated from the uploaded ESG maturity notes. This file normalizes each theme into **stages 0–4**, defines **measurable signals**, **KPIs**, and a **classification contract** (what the scoring service must return).

---

## 0. Cross-cutting grading rules (apply to every theme)

- **Stages:** integer 0–4 only. A higher stage must **inherit** all expectations of lower stages.
- **Evidence requirement:** minimum **2 quotes** (≤30 words) with page numbers per theme stage decision.
- **Contradiction rule:** if any disqualifier is present, cap the stage at the highest stage whose requirements are still fully met.
- **Assurance boost:** if independent assurance is present for the relevant theme data, allow +0.5 confidence (not stage).
- **Time coverage:** disclosures must reference **the scored year** or nearest disclosed year (±1), unless explicitly multi‑year.
- **Output contract (per theme):**
  ```json
  {
    "theme": "<string>",
    "stage": 0,
    "confidence": 0.0,
    "rationale": "<80-word max summary>",
    "evidence": [
      {"quote": "<<=30w>", "page": 1, "section": "string", "chunk_id": "string"}
    ],
    "signals": ["id1","id2"]
  }
  ```

---

## 1. Target setting, planning & decarbonization

**KPI anchors (examples):** presence of SBTi target; coverage of Scopes (1,2, material 3); base year; % reduction; public disclosure; plan depth; scenario analysis; supplier programs; forward-looking milestones.

### Stage 0 — Entry
- **Signals:** No formal targets disclosed for S1/S2/S3.
- **Evidence examples:** “We do not have targets…”, “no targets”, “TBD”.

### Stage 1 — Foundational / Compliance
- Informal/aspirational target text (e.g., “aim to be net zero by 20XX”).  
- May disclose a target publicly, **no** credible plan.  
- **Disqualifiers:** claims without year or scope.  

### Stage 2 — Operational / Efficiency
- Formal target(s): time‑bound intensity or partial scope.  
- Basic progress tracking; public disclosure.  
- References to frameworks (SBTi, GHG Protocol, ISO 14064/14068, ACT, CDP, PAS 2060, TCFD/ISSB).  
- Early pathway/plan exists.  

### Stage 3 — Strategic / Value-creation
- Company‑wide time‑bound targets w/ baseline and S1+S2; partial S3 tracking.  
- Systematic progress tracking; historical trend shown.  
- Company-level plan aligned to long‑range targets.  
- Supplier data quality programs (scorecards/ratings).

### Stage 4 — Transformational
- SBTi‑aligned near‑term + net‑zero incl. material S3.  
- Governance oversight (board/committee).  
- Clear, costed pathway; scenario/what‑if modeling (non‑financial inputs acceptable at minimum).  
- Forward‑looking milestones and supplier decarbonization programs (engagement, circularity, sustainable procurement).

---

## 2. Operational structure & processes

**KPI anchors:** existence of ESG org, RACI/owners, SOPs, training, cross‑functional integration, audits, KPIs tied to BUs, real‑time systems.

### Stage 0 — Entry
- No formal ESG team; no owners; processes ad hoc.

### Stage 1 — Foundational
- Emerging team for compliance; basic documentation; reactive processes.

### Stage 2 — Operational
- Dedicated staff; **some** standardized processes; partial automation for data capture; reporting calendar & ownership.

### Stage 3 — Strategic
- ESG embedded across procurement/operations/finance; detailed SOPs; supplier engagement; continuous improvement (incl. 3rd‑party audits); BU‑level KPIs.

### Stage 4 — Transformational
- Distributed roles aligned to board/executive KPIs; integrated ESG data architecture/real‑time dashboards; advanced supplier programs; forward‑looking KPIs tied to innovation/capital allocation; ESG in strategy & risk.

---

## 3. Data maturity (collection & management)

**Key term:** *Activity data* = quantitative measures (energy, fuels, water, waste, etc.).  
**KPI anchors:** automation level, cadence, centralization, methodology disclosure, validation/audit trail, dashboards, Scope 3 supplier programs, predictive analytics.

### Stage 0 — Entry
- Manual, ad‑hoc, spreadsheet‑based; no governance/ownership.

### Stage 1 — Foundational
- Quarterly/annual manual collection; initial documentation of factors/boundaries; exploring scalable approaches.

### Stage 2 — Operational
- Mostly automated collection; monthly/quarterly cadence; standardized processes across BUs; centralized platform/governance; methodology disclosure; partial audit trails; internal dashboards.

### Stage 3 — Strategic
- Fully automated (or near); integrated & centralized across value chain; full methodology disclosure; full audit trails; continuous improvement; KPI integration & automated tracking; active Scope 3 supplier data program.

### Stage 4 — Transformational
- Integration with ERP/finance/risk/planning; unified governance; real‑time pipelines; predictive analytics & forecasting; dynamic dashboards for internal/external transparency.

---

## 4. GHG accounting

**KPI anchors:** framework alignment, scopes coverage, Y/Y consistency, S3 categories detail, methodology/EF transparency, verification/assurance, baseline management, integration with finance/planning.

### Stage 0 — Entry
- No formal framework; estimates from spend/activity; reactive disclosures; no assurance.

### Stage 1 — Foundational
- Mentions GHG Protocol; first S1/S2 with varying completeness; S3 absent; initial documentation; some internal reviews.

### Stage 2 — Operational
- Implemented framework for S1/S2 (GHG Protocol/CDP/TCFD); partial S3; centralized systems; Y/Y consistent S1/S2; internal verification; 2–4 years disclosed.

### Stage 3 — Strategic
- Comprehensive S1/S2/S3; most of the 15 S3 categories; full third‑party assurance; supplier data program; baseline recalculation policy; 4–6 years disclosed.

### Stage 4 — Transformational
- Real‑time/near‑real‑time accounting; alignment with ISSB/CSRD/GRESB; integrated with finance; dynamic tracking & scenario modeling; 6+ years disclosed and fully assured.

---

## 5. Reporting & disclosure

**KPI anchors:** cadence, process ownership, external assurance, frameworks mapping (GRI/CDP/TCFD/SASB/ISSB), comparability, integration with financial/risk reporting, automation.

### Stage 0 — Entry
- No ESG report; ad‑hoc disclosures; no framework alignment; no assurance.

### Stage 1 — Foundational
- First basic report; small team; loosely structured metrics; partial framework references; some internal reviews.

### Stage 2 — Operational
- Annual report; defined timelines & data owners; S1/S2 consistent; partial S3; framework use increases; some third‑party assurance of key metrics.

### Stage 3 — Strategic
- Multi‑format (integrated report, portals, filings); investor‑grade; external assurance standard; strategic linkage to business/finance; full S3; alignment with global regimes (CSRD/ISSB/GRESB).

### Stage 4 — Transformational
- Fully integrated with financial/risk disclosures (incl. climate risk); automated/near‑real‑time; deep scenario analysis; global regime alignment; transparency on data quality & improvements.

---

## 6. Energy intelligence

**KPI anchors:** EMS presence, metering/telemetry, audits, source mix disclosure, integration with GHG accounting, ISO 50001, renewable sourcing, analytics, demand response/market participation, forecasting.

### Stage 0 — Entry
- No program; manual invoice-based data; reactive; no baseline/targets.

### Stage 1 — Foundational
- Basic tracking; initial dashboards; limited disclosure by type; pilots (lighting/HVAC); early intensity metrics.

### Stage 2 — Operational
- Systematic data collection (utilities/meters); cross-site reporting; energy by source; EMS mention; targets for energy/carbon intensity; ISO 50001 in progress; integration with S1/S2.

### Stage 3 — Strategic
- Cross-functional decision-making; continuous monitoring; integrated EMS; full third‑party audits; integration with S1/S2/S3; renewables strategy (PPAs, onsite, RECs); analytics for savings; tied to SBTi/Net Zero.

### Stage 4 — Transformational
- Real/near‑real‑time systems; integration with procurement/finance/risk; predictive modeling & optimization; demand response/grid services; capital allocation includes transition/resilience.

---

## 7. Risk management & mitigation (draft to be validated)

> The source notes do not yet define this theme. The following is a **proposed** rubric for initial use and SME validation.

### Stage 0 — Entry
- No climate/ESG risk register; ad‑hoc responses to customer questionnaires.

### Stage 1 — Foundational
- Initial identification of transition/physical risks; qualitative heat map; owner assigned; basic controls listed.

### Stage 2 — Operational
- Formal ERM integration; scenario screening for key assets; control testing cadence; linkage to insurance and business continuity.

### Stage 3 — Strategic
- TCFD/ISSB‑aligned risk governance; quantitative risk modeling for material assets; mitigation roadmaps with budgets; supplier risk assessment integrated.

### Stage 4 — Transformational
- Enterprise climate risk engine (financial linkage, VaR, stress testing); portfolio rebalancing; adaptation investments tracked; risk metrics embedded in capital planning & incentives.

---

## 8. Scoring math

- **Theme stage:** 0–4.  
- **Overall maturity:** simple mean of theme stages (weighting configurable per business need).  
- **Confidence (0–1):** LLM self‑report (scaled) × evidence strength (count/diversity) × assurance factor.  
- **Minimum evidence:** 2 quotes with page refs per theme.

---

## 9. Evidence taxonomy (signal IDs)

Use these canonical signal IDs in extraction/labeling to keep things consistent across prompts and evals.

- `public_target_disclosed`
- `sbt_i_aligned`
- `scope1_2_covered`
- `material_scope3_included`
- `plan_with_milestones`
- `governance_board_oversight`
- `progress_tracked_yearly`
- `supplier_scorecards`
- `scenario_modeling_present`
- `esg_team_exists`
- `sops_documented`
- `cross_function_integration`
- `data_automation_present`
- `central_platform_present`
- `methodology_disclosed`
- `audit_trail_present`
- `third_party_assurance`
- `scope3_categories_disclosed`
- `frameworks_mapped_gri_cdp_tcfD_sasb_issb`
- `integrated_with_finance`
- `ems_present`
- `renewable_strategy_active`
- `predictive_energy_modeling`
- `demand_response_participation`
- `climate_risk_registered`
- `tcfd_issb_alignment`
- `supplier_risk_assessed`

---

## 10. API contract alignment

The grading service MUST return, for each company/year/theme, the JSON object defined above (Section 0). Store records to:
- **AstraDB**: `scores.maturity_by_company_year`
- **Parquet**: partitioned by `company=<name>/year=<yyyy>` with columns:
  - `company, year, theme, stage, confidence, evidence_ids[], model_version, rubric_version`

---

## 11. Prompting hints (watsonx.ai)

- **Extraction prompt:** “Return JSON array of findings with fields: `chunk_id, quote<=30w, page, section, theme, signals[] (ids)`. Use only the provided context.”  
- **Classification prompt:** “Given findings for `<theme>` and rubric v1.0, output `{theme, stage (0–4), confidence, rationale<=80w, evidence:[{quote,page,chunk_id}]}`.”

---

## 12. Change log

- v1.0 — Initial normalization from source notes; Risk Management drafted pending SME review.