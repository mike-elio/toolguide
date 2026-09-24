# Catalog corrections — 2026-09-06

Scope: bounded official-source review of five high-risk expanded records and three replacement entries. No claim of a complete catalog audit. Sources accessed September 6, 2026; undated pages are identified below. Recommendation signals are editorial classifications, not independently proven capability gates.

## Product identity and availability

- **Elastic Enterprise Search → Docling.** [Elastic migration documentation](https://www.elastic.co/guide/en/enterprise-search/current/upgrading-to-9-x.html) (Elastic, undated) says Enterprise Search is unavailable in 9.0 onward; existing customers can retain 8.x and new post-9.0 customers cannot access it. [Product-team announcement](https://www.elastic.co/blog/search-for-enterprise-serverless) (April 15, 2025) confirms deprecation. Docling fills an analysis/software catalog slot for document conversion; it is not a drop-in replacement for enterprise search.
- **Sophos X-Ops → OpenCTI Community Edition.** [Sophos X-Ops](https://www.sophos.com/en-us/x-ops) (Sophos, undated) describes an initiative and cross-functional team. Treating this research organization as a standalone installable tool was inappropriate. OpenCTI is a distinct threat-intelligence platform.
- **RiskLens FAIR Platform → SAFE One.** [SAFE's 2024 review](https://safe.security/resources/blog/safe-security-year-in-review-2024-cybersecurity-milestones/) (Sachin Jha / SAFE, December 30, 2024) records the 2023 acquisition, SAFE One launch, and approximately 80% customer migration by Q2 2024. [Current product overview](https://safe.security/product-overview/) (SAFE, undated) identifies SAFE One and cyber-risk quantification. This establishes a current successor without claiming universal RiskLens shutdown.
- **Mandiant Advantage Threat Intelligence retained.** [Google security status dashboard](https://status.cloud.google.com/security/) (Google, live) lists both Mandiant Advantage Threat Intelligence and Google Threat Intelligence. [GTI product page](https://cloud.google.com/security/products/threat-intelligence) (Google, undated) identifies Mandiant intelligence as an input. This supports overlap, not a forced merge or discontinuation claim. Exact entitlements must be checked; the GTI source URL is shared and does not prove that every GTI feature belongs to the Mandiant subscription. The unsupported GTI limitation about non-Google SOC environments is replaced with an integration/entitlement check.
- **Phind unresolved.** Official root and blog retrieval failed, including HTTP 404 for `https://phind.com/` and `https://www.phind.com/blog`. No official shutdown announcement was retrieved. These access failures do not establish closure or its date; the entry was not changed in this correction pass.

## Replacement evidence and starter workflows

### Docling (`docling`, focus `document_conversion`)

[Official documentation](https://docling-project.github.io/docling/) (Docling project, undated) supports document parsing, OCR, layout/table interpretation, export and local execution. [Repository](https://github.com/docling-project/docling) states MIT for the codebase with individual model licenses separate. [Advanced options](https://docling-project.github.io/docling/usage/advanced_options/) explains model preparation for offline environments. Do not infer that optional remote services operate offline.

[Quickstart](https://docling-project.github.io/docling/getting_started/quickstart/) demonstrates `DocumentConverter().convert(source).document` and `export_to_markdown()`. Editorial starter: install in a Python environment, convert one local document, and review table structure and reading order before bulk use.

### OpenCTI (`opencti`, focus `threat_intelligence`)

[Repository](https://github.com/OpenCTI-Platform/opencti) (Filigran, undated) identifies the platform and separates Apache-2.0 Community Edition from the Enterprise Edition license. [Deployment overview](https://docs.opencti.io/latest/deployment/overview/) documents the maintained dependency stack. External feed access and Enterprise features require separate validation.

[Installation](https://docs.opencti.io/latest/deployment/installation/) demonstrates cloning the official Docker repository, configuring `.env` from `.env.sample` with a valid administrator token, starting `docker compose up -d`, and opening `http://localhost:8080` with configured credentials. This is setup evidence, not a claim that all external feeds work offline.

### SAFE One (`safe-one`, focus `quantitative_risk`)

[Current overview](https://safe.security/product-overview/) (SAFE, undated) presents enterprise/third-party risk management, quantification and demo access. The dated review above supplies FAIR and RiskLens migration provenance. No specific price, open-source license or offline entitlement is asserted.

Editorial starter: use the official demo, define a risk scenario and its business assumptions, confirm licensed modules/integrations, and review quantified outputs with a domain expert. These are suggested review activities, not verified UI instructions.

## Localization and remaining limits

Expanded Arabic descriptions now use explicit Arabic focus labels instead of English identifiers or a generic assertion that every workflow was verified against its source. Four reviewed records have specific bilingual caveats; remaining generic caveats are not an assertion of complete verification. IriusRisk and ThreatModeler already exist, so neither was duplicated as a replacement. No pricing, deployment or feature entitlement is invented to fill missing evidence.
