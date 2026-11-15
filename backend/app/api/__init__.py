"""API routes. Each module in this package that defines a module-level `router` (a FastAPI
APIRouter) is included automatically by app.main, in alphabetical order of module name.

To add a feature's routes, add a module here; do not edit app/main.py. This keeps phases that
run in parallel from editing the same file.
"""

from __future__ import annotations

import importlib
import pkgutil

from fastapi import APIRouter


def discover_routers() -> list[APIRouter]:
    routers: list[APIRouter] = []
    for module_info in sorted(pkgutil.iter_modules(__path__), key=lambda info: info.name):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            routers.append(router)
    return routers
