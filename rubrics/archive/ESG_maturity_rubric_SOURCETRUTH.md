ESG Maturity Rubric — v2.0 (Aligned to Source Document)
This specification directly transcribes the requirements from the ESG Doc.docx into an implementation-ready rubric. It is designed to instruct an LLM on the precise evaluation criteria and output format defined in that source.

1. Agent Task & Output Specification
Your primary task is to evaluate an organization's maturity for a single specified theme, based on its ESG report and the rubric definitions below. You must then produce a two-part response.

1.1. Output Part 1: Evidence Table
Generate a table listing up to ten compelling insights that justify the maturity stage assessment.


Prioritization: Rows must be prioritized, with the strongest evidence listed first.

Table Structure:


Column 1 (Priority Score): The rank number.


Column 2 (Characteristic): A description of the characteristic from the rubric for which you found evidence.


Column 3 (Evidence Extract): An exact extract from the source material (30 words max) providing the evidence.


Column 4 (Maturity Stage): The stage (e.g., "Stage 1", "Stage 2") that the characteristic suggests.

1.2. Output Part 2: Envizi Pitch Table
Generate a second table listing the IBM Envizi solutions to pitch, based on the organization's assessed maturity.


Goal: The pitch must clearly state how a feature helps the organization improve in maturity.

Table Structure:


Column 1 (Row Number): The row number.


Column 2 (Envizi Solution): The Envizi solution being pitched.


Column 3 (Features): The features you would pitch.


Column 4 (Rationale): A bulleted list of reasons (20-30 words each) why the organization would benefit from this feature.


Knowledge Base: Use these links for feature descriptions:


https://www.ibm.com/products/envizi/target-setting-tracking 


https://www.ibm.com/products/envizi/sustainability-program-tracking 


https://www.ibm.com/products/envizi/sustainability-planning 


https://www.ibm.com/products/envizi/supply-chain 

2. Rubric Theme: Target setting, planning and decarbonisation
Stage 0: Entry-level tooling
No formal ESG or emissions reduction targets for Scope 1, Scope 2 or Scope 3.

Stage 1: Foundational/ Compliance-driven
Informal or broad ESG or emissions reduction target (e.g., "reduce emissions by X% by year YYYY", or "net zero emissions by YYYY").

May have a public disclosure of ESG or emissions reduction target.

No or little evidence of planning that shows the organisation is thinking about a pathway to reducing emissions.

Stage 2: Operational/ Efficiency-oriented
Formal ESG or emissions reduction targets defined (e.g., "reduce emissions by X% by year YYYY", or "net zero emissions by YYYY").

Evidence of broad but not formal tracking of progress against emissions reduction targets.

May have targets aligned to formal methodologies and frameworks (e.g., SBTi, GHG Protocol, ISO 14064, ISO 14068, ACT Initiative, CDP, PAS 2060, TCFD/ISSB, Net Zero commitment).

Has a public disclosure of ESG or emissions reduction target.

Some evidence of planning processes that try and define a pathway to emissions reduction.

May be tracking progress towards formal ESG or emissions reduction targets.

Stage 3: Strategic/ Value-creation focused
Formal ESG or emissions reduction targets defined (e.g., "reduce emissions by X% by year YYYY", or "net zero emissions by YYYY").

Evidence of systematic tracking of progress against emissions reduction targets.

Has targets aligned to formal methodologies and frameworks (e.g., SBTi, GHG Protocol, ISO 14064, ISO 14068, ACT Initiative, CDP, PAS 2060, TCFD/ISSB, Net Zero commitment).

Has a public disclosure of ESG or emissions reduction target.

Evidence of planning processes that try and define a pathway to emissions reduction.

Emissions reduction plans show alignment to long-range ESG or emissions reduction targets on a company-level.

Evidence of tracking historical progress against formal ESG or emissions reduction targets.

Evidence of decarbonisation efforts to better understand sources of Scope 3 emissions (e.g., tools to evaluate data quality, supplier scorecards, or rating systems).

Stage 4: Transformational
Formal ESG or emissions reduction targets defined.

Evidence of systematic tracking of progress against targets.

Evidence of governance oversight (e.g., committees, boards) monitoring progress.

Has targets aligned to formal methodologies and frameworks (e.g., SBTi, GHG Protocol, ISO 14064, ISO 14068, ACT Initiative, CDP, PAS 2060, TCFD/ISSB, Net Zero commitment).

Has a public disclosure of the target.

Evidence of planning processes that define a clear pathway to emissions reduction or net zero targets.

Plans show alignment to long-range targets with company-level breakdowns.

Evidence of scenario modeling, what-if analysis or simulation tools (which may not incorporate financial information).

Evidence of tracking historical progress.

Evidence of forward-looking KPIs, metrics or milestones to understand trajectory.

Evidence of decarbonisation efforts to reduce Scope 3 emissions (e.g., supplier engagement, circular design, low-carbon procurement) .

Evidence of conducting supplier risk assessments.

3. Rubric Theme: Operational structure and processes
Stage 0: Entry-level tooling
No formal sustainability team.

Lack of stated ESG governance or process owners; no repeatable processes.

Stage 1: Foundational/ Compliance-driven
Emerging ESG or sustainability team focused on compliance (Mention of establishing governance or assigning responsibilities).

Basic documentation of ESG processes, but still fragmented.

ESG processes are primarily reactive and compliance-focused.

Stage 2: Operational/ Efficiency-oriented
Dedicated ESG staff with standardized internal processes (References to internal ESG training or SOPs).

Some documented procedures for GHG data collection and validation.

Partial automation of data gathering (utility data, facility-level uploads).

Defined reporting calendar and ownership roles.

Stage 3: Strategic/ Value-creation focused
Dedicated ESG staff with standardized internal processes (References to internal ESG training or SOPs).

ESG operationalized across procurement, operations, and finance.

Detailed documented procedures for GHG data collection and validation.



Integrated GHG data collection and reporting across value chain.

Supplier engagement and Scope 3 process integration.

Defined reporting calendar and ownership roles.

Continuous improvement process for ESG data quality and validation (3rd party audits).

Internal ESG performance KPIs tied to business units.

Stage 4: Transformational
(Contains all characteristics of Stage 3) .



Additional ESG roles distributed across the organization (governance linked to board-level strategy and executive KPIs).

Integrated systems for capturing and managing ESG data (Mentions of “integrated ESG data architecture” or “real-time ESG dashboarding”).

Advanced supplier engagement and data collection to drive continuous improvement of Scope 3 accuracy.

Forward-looking KPI metrics tied to innovation, capital allocation, or business transformation.

ESG embedded in strategic planning, risk management, and innovation.

Carbon accounting integrated into enterprise decision-making and innovation cycles.

4. Rubric Theme: Data maturity (collection and management)
Stage 0: Entry-level tooling
Site-level or facility-level activity data is collected manually and ad-hoc.

Data collection is manual, unstructured, and dispersed (not centralized, often in spreadsheets).

Emissions are calculated using spreadsheets.

No formal data documentation, ownership, validation process or governance.

Stage 1: Foundational/ Compliance-driven
Site-level or facility-level activity data is collected manually, often quarterly or annually.

Some or basic efforts to structure ESG and GHG data collection processes.

Data collection continues to be manual, unstructured, and dispersed (spreadsheets).

Emissions are calculated using spreadsheets but more structured and scalable approaches are being explored.

Initial documentation of emission factors, sources, and boundaries.

Early description of data collection methods with inconsistent version control.

Stage 2: Operational/ Efficiency-oriented
Site-level or facility-level activity data collected mostly or completely automated.

Activity data collection conducted on a more regular basis (e.g. monthly or quarterly).

Efficiency-focussed efforts to structure ESG and GHG data collection processes (e.g., standardized processes).

Centralized internal ESG platform, shared database and/or governance process.

Full disclosures of clear data collection methodologies, sources, and emission factors.

Data validation and audit trails partially implemented by internal or external assurance.

Evidence of internal dashboards used for GHG and energy performance tracking.

Stage 3: Strategic/ Value-creation focused
Site-level or facility-level activity data completely (or almost completely) collected via automated means.

Standardized and efficient data management processes across business units.

Integrated and fully centralized GHG data collection (ESG data platform).

Full disclosures of clear data collection methodologies, sources, and emission factors.

Data validation and audit trails fully implemented by internal or external assurance.

Evidence of continuous improvement processes for data completeness and validation.

Evidence of internal dashboards used for tracking.

Evidence of KPI integration and automated progress tracking against targets.

Scope 3 data actively managed through suppliers.

Stage 4: Transformational
(Contains all characteristics of Stage 3) .



ESG data integrated into enterprise systems (ERP, finance, risk, and planning).

Unified governance and data standards applied across sustainability, risk, and finance.

Dynamic dashboards for internal decision-making and external transparency.

Real-time ESG data collection, flow and automated reporting systems.

Predictive analytics and AI used for forecasting emissions and scenario modeling.

5. Rubric Theme: GHG accounting
Stage 0: Entry-level tooling
No formal GHG accounting framework or defined emission boundaries/methodology.

Emissions data estimated manually or extrapolated from spend or activity data.

Only high-level totals (Scope 1 & 2), often based on assumptions.

Reactive GHG disclosures driven by buyer or customer requests.

No assurance, verification, or internal review of calculations.

Stage 1: Foundational/ Compliance-driven
Mentions of the GHG Protocol or similar basic accounting standards.

First disclosures of Scope 1 and Scope 2 emissions calculated with varying completeness (no Scope 3).

Exclusion of material sources explained as “data not yet available”.

Initial documentation of methodology, emission factors, etc., but not consistent.

Some assurance, verification, all internal reviews of calculations.

Reporting may include at least one year of data with inconsistent methodology notes.

Stage 2: Operational/ Efficiency-oriented
GHG accounting framework implementation for Scope 1 and 2, aligned with frameworks (GHG Protocol, CDP, TCFD).

Disclosure of consistent Scope 1 & 2 data year-over-year.


Partial inclusion of Scope 3 categories with logical boundaries.

Use of centralized data systems to automate emission factor calculations.

Clear disclosure of methodology, emission factors, sources, and organizational boundaries.

Internal verification or review of data accuracy, maybe some 3rd party audits mentioned.

Improving methodology accuracy or mentions intent to do so.

Reporting includes 2-4 years of data with consistent methodology notes.

Stage 3: Strategic/ Value-creation focused
Comprehensive accounting of Scope 1, 2, and 3, aligned to recognized frameworks.

Disclosure of consistent Scope 1, 2, 3 data year-over-year.

Use of centralized data systems to automate emission factor calculations.

Calculation and reporting of most 15 Scope 3 categories with details on data sources.

Clear disclosure of methodology, emission factors, sources, and boundaries.


Full third-party assurance of Scope 1, Scope 2, and all Scope 3 categories.

Actively improving methodology accuracy (e.g., supplier engagement, product carbon footprint).

Reporting includes 4-6 years of data plus baseline emissions.

Regular recalculation or intent to recalculate baselines.

Stage 4: Transformational
(Contains all characteristics of Stage 3) .




Real-time or near-real-time carbon accounting integrated with operational systems (e.g., ERP, IoT).

Alignment with regulatory or market standards (e.g., ISSB, CSRD, GRESB).

Mention of integration between GHG data and financial disclosures (e.g., TCFD or CSRD reporting).

GHG accounting fully embedded in business strategy, forecasting, and risk modeling.

Dynamic GHG performance tracking with predictive and scenario-based modeling.

6. Rubric Theme: Reporting and disclosure process
Stage 0: Entry-level tooling
No formal ESG or sustainability report produced.

Disclosures are ad hoc, reactive, and customer-driven.

ESG or emissions data shared only on request, with no public reporting.

No alignment with recognized frameworks or standards (GRI, CDP, TCFD, etc.).

No assurance validation.

Stage 1: Foundational/ Compliance-driven
May have published first sustainability or ESG report, often brief and compliance-oriented.

Disclosures guided by emerging stakeholder interest or regulatory awareness.

Reporting handled by a small team or communications function.

ESG content loosely structured; basic metrics (energy, emissions, waste) reported.

Narrative focus on initiatives rather than performance data.

No consistent year-over-year comparability; minimal governance disclosure.

Partial or informal use of frameworks (e.g., GRI references).

Some assurance, verification, all internal reviews.

Stage 2: Operational/ Efficiency-oriented
Regular (annual) ESG or sustainability report established.

Structured reporting process with defined timelines, data owners, and verification steps.

Improved internal coordination between departments.

Disclosure of consistent Scope 1 & 2 data year-over-year with partial inclusion of Scope 3.

More detailed emissions disclosures with footnotes on methodology.

Clearer year-over-year comparisons and progress metrics.

Increasing use of external frameworks: GRI, CDP, SASB, or TCFD references.

Mostly internal assurance processes with some 3rd party assurance of key metrics.

Stage 3: Strategic/ Value-creation focused
Regular (annual) ESG or sustainability report established.


Multi-format reporting: integrated annual report, ESG data portals, and regulatory filings.

External assurance is standard; ESG reporting part of investor-grade disclosures.

Structured reporting process with defined timelines, data owners, and verification steps.

Streamlined internal coordination between departments.

Clear linkage between ESG performance, business strategy, and financial outcomes.

Disclosure of consistent Scope 1 & 2 data year-over-year with full Scope 3 data.

Clearer year-over-year comparisons and progress metrics.

Integration of multiple frameworks: GRI, CDP, TCFD, SBTi, and SASB or ISSB drafts.

Aligned with some global reporting regimes (CSRD, ISSB, GRESB, or regional taxonomies).

External assurance (limited or reasonable) for key ESG metrics.

Transparency around data quality and improvement plans.

ESG reporting becomes strategically embedded in business performance.

Stage 4: Transformational
(Contains all characteristics of Stage 3) .


ESG reporting is fully integrated with financial, risk, and strategic disclosures, also includes climate risk.

Use of real-time or near-real-time data and automated disclosure systems.

Deep scenario analysis and forward-looking metrics embedded in reporting.

7. Rubric Theme: Energy intelligence
Stage 0: Entry-level tooling
No formal energy management program or policy.

Energy data collected inconsistently and manually (e.g., from invoices, excel based).

Reactive approach: energy management addressed only when requested.

No distinction between energy types.

No defined energy baseline or reduction programs/targets.

Stage 1: Foundational/ Compliance-driven
Dedicated processes or teams for energy tracking and performance improvement.

Early-stage data gathering on energy consumption and fuel use.

Initial internal tracking via spreadsheets or simple dashboards.

Limited disclosure of total energy consumption or energy use by type.

Early energy intensity metrics (e.g., kWh per product).

All internal review/assurance processes.

Basic energy reporting and benchmarking.

Pilot efficiency projects initiated (lighting, HVAC, etc.).

Stage 2: Operational/ Efficiency-oriented
Dedicated processes or teams for energy tracking.


Systematic data collection from utilities, meters, or internal systems.

Regular reporting of performance across sites or business units with partial energy audits.

Disclosure of energy consumption by source (renewable vs. non-renewable).

Mention of energy management systems (EMS) or standardized reporting tools.

Integration of energy data with Scope 1 and 2 GHG accounting.


Some 3rd party audits, still mostly internal.

Defined reduction targets for energy and/or carbon intensity.

Company-wide energy efficiency programs or ISO 50001 certification in progress.

Early stages of energy management embedded in broader strategy.

Stage 3: Strategic/ Value-creation focused
Dedicated processes or teams for energy tracking.

Systematic data collection from utilities, meters, or internal systems.

Procurement and operations teams involved in energy decision-making.


Continuous monitoring of site-level or asset-level energy performance.

Consistent reporting of performance across sites.

Disclosure of energy consumption by source (renewable vs. non-renewable).

Fully integrated energy management systems (EMS).


Full 3rd party audits of externally reported metrics.

Integration of energy data with Scope 1, 2, 3 GHG accounting.

Defined reduction targets for energy and/or carbon intensity.

Company-wide energy efficiency programs or ISO 50001 certification.

Energy management embedded in broader carbon reduction and sustainability strategy.

Energy and GHG performance tied to corporate Net Zero or SBTi commitments.


Active pursuit of renewable energy sourcing (PPAs, on-site solar, RECs, etc.).

Advanced analytics used to track energy performance and identify savings.


Stage 4: Transformational
(Contains all characteristics of Stage 3) .


Energy management is fully integrated with procurement, operations, financial planning, risk, and innovation.


Real-time or near-real-time energy and carbon data systems.

Discussion of energy as a driver of innovation, competitiveness, or business model change.


Predictive modeling used for energy forecasting and optimization.


Active participation in energy markets, grid services, or demand response programs.

Capital allocation decisions include energy transition and resilience considerations.

8. Rubric Theme: Risk management and mitigation
Stage 0: Entry-level tooling


No characteristics defined in source document.

Stage 1: Foundational/ Compliance-driven


No characteristics defined in source document.

Stage 2: Operational/ Efficiency-oriented


No characteristics defined in source document.

Stage 3: Strategic/ Value-creation focused


No characteristics defined in source document.

Stage 4: Transformational


No characteristics defined in source document