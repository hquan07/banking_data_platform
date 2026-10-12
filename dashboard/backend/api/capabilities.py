"""Authenticated, versioned dashboard capability manifest."""

from fastapi import APIRouter, Depends, HTTPException, Query

from core.deps import get_current_user
from services.capabilities import (
    MANIFEST_VERSION,
    SUPPORTED_MANIFEST_VERSIONS,
    UnsupportedManifestVersion,
    build_capability_manifest,
)
from services.runtime_readiness import load_runtime_readiness


router = APIRouter(
    prefix="/api/capabilities", tags=["Capabilities"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
def get_capabilities(version: int = Query(MANIFEST_VERSION, ge=1)):
    try:
        return build_capability_manifest(load_runtime_readiness(), version=version)
    except UnsupportedManifestVersion as exc:
        raise HTTPException(
            status_code=406,
            detail={
                "message": "Unsupported capability manifest version",
                "requested_version": version,
                "supported_versions": sorted(SUPPORTED_MANIFEST_VERSIONS),
            },
        ) from exc

