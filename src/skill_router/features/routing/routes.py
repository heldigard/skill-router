"""Structured routing table for skill-router.

Each route declares regex patterns, the compact hook hint, and machine-readable
metadata for skill loading, tool routing, workers, and documentation namespaces.
Priority controls which matched hints survive the UserPromptSubmit budget; source
order breaks ties.
"""

from __future__ import annotations

from .route import Route
from .route_groups.core import CORE_ROUTES
from .route_groups.delivery import DELIVERY_ROUTES
from .route_groups.platform_cloud import PLATFORM_CLOUD_ROUTES
from .route_groups.tools_misc import TOOLS_MISC_ROUTES
from .route_groups.web_frontend import WEB_FRONTEND_ROUTES
from .route_groups.workflow import WORKFLOW_ROUTES

ROUTES: list[Route] = [
    *CORE_ROUTES,
    *WEB_FRONTEND_ROUTES,
    *PLATFORM_CLOUD_ROUTES,
    *DELIVERY_ROUTES,
    *WORKFLOW_ROUTES,
    *TOOLS_MISC_ROUTES,
]
