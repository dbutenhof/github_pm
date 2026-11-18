"""Repository metadata, revalidated through the scoped HTTP cache.

Generated-by: Codex
"""

import re

VERSION_MATCH = re.compile(r"^v\d+\.\d+\.\d+$")


def catalog(gitctx, resource, *, state=None):
    path = f"/repos/{gitctx.owner}/{gitctx.repo}/{resource}"
    if state:
        path += f"?state={state}"
    return gitctx.get_paged(
        path, headers={"Accept": "application/vnd.github.full+json"}
    )


def milestone_catalog(gitctx):
    items = catalog(gitctx, "milestones", state="all")
    return (
        [m for m in items if m["state"] == "open"],
        [m for m in items if m["state"] == "closed"],
    )
