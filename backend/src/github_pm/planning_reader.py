"""Focused, batched reads for Planning and hierarchy commands.

Generated-by: Codex
"""

from github_pm.report_queries import complete_connections, execute, PAGE

DEPENDENCY = "databaseId number title url state"
CLOSING = "number title url"
PARENT = "parent { number title milestone { number title } }"
IDENTITY = "id databaseId number title url state milestone { number title }"
LINKS = (
    "closedByPullRequestsReferences(first:100,includeClosedPrs:true) { nodes { "
    + CLOSING
    + " } "
    + PAGE
    + " } blockedBy(first:100) { nodes { "
    + DEPENDENCY
    + " } "
    + PAGE
    + " } blocking(first:100) { nodes { "
    + DEPENDENCY
    + " } "
    + PAGE
    + " }"
)
REACTION = "content user { login }"
REACTIONS = "reactions(first:100) { nodes { " + REACTION + " } " + PAGE + " }"
_REACTION_NAMES = {
    "THUMBS_UP": "+1",
    "THUMBS_DOWN": "-1",
    "LAUGH": "laugh",
    "HOORAY": "hooray",
    "CONFUSED": "confused",
    "HEART": "heart",
    "ROCKET": "rocket",
    "EYES": "eyes",
}


def _post(gitctx):
    return lambda payload: gitctx.post("/graphql", payload)


def issue_nodes(gitctx, numbers, fields=IDENTITY, *, issue_only=False):
    """Use independent aliases so callers need only repository-local numbers."""
    numbers = list(dict.fromkeys(numbers))
    result = {}
    for offset in range(0, len(numbers), 50):
        batch = numbers[offset : offset + 50]
        variables = {"owner": gitctx.owner, "repo": gitctx.repo}
        definitions, selections = ["$owner:String!", "$repo:String!"], []
        for i, number in enumerate(batch):
            definitions.append(f"$n{i}:Int!")
            variables[f"n{i}"] = number
            if issue_only:
                selection = f"issue(number:$n{i}) {{ __typename {fields} }}"
            else:
                selection = f"issueOrPullRequest(number:$n{i}) {{ __typename ... on Issue {{ {fields} }} ... on PullRequest {{ {IDENTITY} }} }}"
            selections.append(f"i{i}:" + selection)
        data = execute(
            _post(gitctx),
            "query("
            + ",".join(definitions)
            + ") { repository(owner:$owner,name:$repo) { "
            + " ".join(selections)
            + " } rateLimit { cost } }",
            variables,
        )
        repository = data.get("repository") or {}
        for i, number in enumerate(batch):
            node = repository.get(f"i{i}")
            if not node:
                raise RuntimeError(f"GitHub issue #{number} is missing or inaccessible")
            result[number] = node
    return result


def enrich_issues(gitctx, issues):
    if not issues:
        return {}
    nodes = issue_nodes(
        gitctx,
        [i["number"] for i in issues],
        "id number " + PARENT + " " + LINKS,
        issue_only=True,
    )
    complete_connections(
        _post(gitctx),
        list(nodes.values()),
        "Issue",
        {
            "blockedBy": (DEPENDENCY, ""),
            "blocking": (DEPENDENCY, ""),
            "closedByPullRequestsReferences": (CLOSING, "includeClosedPrs:true"),
        },
    )
    return nodes


def descendants(gitctx, root):
    """Breadth-first traversal includes closed and cross-milestone descendants."""
    found, frontier, seen = [], [root], {root}
    while frontier:
        nodes = issue_nodes(
            gitctx,
            frontier,
            "id number subIssues(first:100) { nodes { number } " + PAGE + " }",
            issue_only=True,
        )
        complete_connections(
            _post(gitctx), list(nodes.values()), "Issue", {"subIssues": ("number", "")}
        )
        frontier = []
        for node in nodes.values():
            for child in node["subIssues"]["nodes"]:
                number = child["number"]
                if number not in seen:
                    seen.add(number)
                    found.append(number)
                    frontier.append(number)
    return found


def rest_identity(node):
    result = dict(node, id=node["databaseId"], node_id=node["id"], html_url=node["url"])
    if node["__typename"] == "PullRequest":
        result["pull_request"] = {}
    return result


def comment_reactions(gitctx, comments):
    """Batch reaction enrichment; keep REST bodies/IDs for editing fidelity."""
    targets = [
        c for c in comments if (c.get("reactions") or {}).get("total_count", 0) > 0
    ]
    for offset in range(0, len(targets), 50):
        batch = targets[offset : offset + 50]
        if any(not c.get("node_id") for c in batch):
            raise RuntimeError("GitHub omitted comment node IDs")
        data = execute(
            _post(gitctx),
            "query($ids:[ID!]!) { nodes(ids:$ids) { ... on IssueComment { id "
            + REACTIONS
            + " } } rateLimit { cost } }",
            {"ids": [c["node_id"] for c in batch]},
        )
        nodes = {n["id"]: n for n in data.get("nodes") or [] if n}
        if len(nodes) != len(batch):
            raise RuntimeError("GitHub omitted comment reactions")
        complete_connections(
            _post(gitctx),
            list(nodes.values()),
            "IssueComment",
            {"reactions": (REACTION, "")},
        )
        for comment in batch:
            comment["reaction_details"] = [
                dict(content=_REACTION_NAMES[r["content"]], user=r.get("user"))
                for r in nodes[comment["node_id"]]["reactions"]["nodes"]
            ]
    return comments
