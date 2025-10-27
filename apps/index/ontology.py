from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

class NodeType(str, Enum):
    COMPANY = "Company"
    REPORT = "Report"
    TARGET = "Target"
    METRIC = "Metric"
    FRAMEWORK = "Framework"
    GOV_BODY = "GovernanceBody"

class EdgeType(str, Enum):
    REPORT_OF = "REPORT_OF"
    HAS_TARGET = "HAS_TARGET"
    REPORTS_METRIC = "REPORTS_METRIC"
    ALIGNS_WITH = "ALIGNS_WITH_FRAMEWORK"
    OVERSEEN_BY = "OVERSEEN_BY"

@dataclass(frozen=True)
class Node:
    id: str
    type: NodeType
    props: Dict[str, Any]

@dataclass(frozen=True)
class Edge:
    src: str
    rel: EdgeType
    dst: str
    props: Dict[str, Any] | None = None
