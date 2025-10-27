# ADR-001: PyMuPDF for PDF Extraction
**Status**: Accepted
**Decision**: Use PyMuPDF (fitz) for PDF parsing
**Rationale**: Faster than pdfminer, better layout detection, handles images

# ADR-002: Append-Only Bronze Layer
**Status**: Accepted
**Decision**: Bronze layer is immutable, append-only
**Rationale**: Simplifies consistency, enables audit trail, supports time-travel

# ADR-003: MCP for Crawler Tools
**Status**: Accepted
**Decision**: Implement crawler as MCP agent with tool-based interface
**Rationale**: Standardized protocol, enables agent orchestration
