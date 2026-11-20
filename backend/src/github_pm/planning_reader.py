"""Focused, batched reads for Planning and hierarchy commands.

Generated-by: Codex
"""

from github_pm.report_queries import complete_connections, execute, next_cursor, PAGE

DEPENDENCY = "databaseId number title url state"
CLOSING = "number title url"
PARENT = "parent { number title milestone { number title } }"
IDENTITY = "id databaseId number title url state milestone { number title }"
FIELD_VALUE_NODE = (
    "__typename "
    "... on IssueFieldSingleSelectValue { name value optionId color "
    "field { ... on IssueFieldSingleSelect { id name dataType } } } "
    "... on IssueFieldMultiSelectValue { value "
    "field { ... on IssueFieldMultiSelect { id name dataType } } } "
    "... on IssueFieldNumberValue { value "
    "field { ... on IssueFieldNumber { id name dataType } } } "
    "... on IssueFieldTextValue { value "
    "field { ... on IssueFieldText { id name dataType } } } "
    "... on IssueFieldDateValue { value "
    "field { ... on IssueFieldDate { id name dataType } } }"
)
FIELD_VALUES = "issueFieldValues(first:100) { nodes { " + FIELD_VALUE_NODE + " } }"
ISSUE_FIELD_NODE = (
    "__typename "
    "... on IssueFieldDate { id name dataType } "
    "... on IssueFieldNumber { id name dataType } "
    "... on IssueFieldText { id name dataType } "
    "... on IssueFieldMultiSelect { id name dataType "
    "options { id name color priority } } "
    "... on IssueFieldSingleSelect { id name dataType "
    "options { id name color priority } }"
)
SET_FIELD_VALUE = (
    "mutation($issueId:ID!, $fieldId:ID!, $optionId:ID!) { "
    "setIssueFieldValue(input:{issueId:$issueId, "
    "issueFields:[{fieldId:$fieldId, singleSelectOptionId:$optionId}]}) { "
    "issue { id number issueFieldValues(first:100) { nodes { "
    + FIELD_VALUE_NODE
    + " } } } } }"
)
DELETE_FIELD_VALUE = (
    "mutation($issueId:ID!, $fieldId:ID!) { "
    "setIssueFieldValue(input:{issueId:$issueId, "
    "issueFields:[{fieldId:$fieldId, delete:true}]}) { "
    "issue { id number issueFieldValues(first:100) { nodes { "
    + FIELD_VALUE_NODE
    + " } } } } }"
)
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


def _normalized_field_values(nodes):
    """Normalize GraphQL issue field values for the Planning payload.

    Generated-by: Cline
    """
    values = []
    for value in nodes or []:
        field = value.get("field") or {}
        normalized = {
            "field_id": field.get("id"),
            "field_name": field.get("name"),
            "data_type": field.get("dataType"),
            "value": value.get("value"),
        }
        if value.get("optionId") is not None:
            normalized["option_id"] = value["optionId"]
        if value.get("color") is not None:
            normalized["color"] = value["color"]
        values.append(normalized)
    return values


def _normalized_issue_field(field):
    """Normalize one repository issue field definition.

    Generated-by: Cline
    """
    normalized = {
        "id": field.get("id"),
        "name": field.get("name"),
        "data_type": field.get("dataType"),
    }
    options = field.get("options")
    if options is not None:
        normalized["options"] = [
            {
                "id": option.get("id"),
                "name": option.get("name"),
                "color": option.get("color"),
                "priority": option.get("priority"),
            }
            for option in sorted(options, key=lambda item: item.get("priority") or 0)
        ]
    return normalized


def issue_fields(gitctx):
    """Return the repository's issue fields and whether the viewer can see them.

    Generated-by: Cline
    """
    fields, cursor, can_view = [], None, False
    while True:
        data = execute(
            _post(gitctx),
            "query($owner:String!,$repo:String!,$after:String) { "
            "repository(owner:$owner,name:$repo) { viewerCanSeeIssueFields "
            "issueFields(first:100,after:$after) { nodes { "
            + ISSUE_FIELD_NODE
            + " } "
            + PAGE
            + " } } rateLimit { cost } }",
            {"owner": gitctx.owner, "repo": gitctx.repo, "after": cursor},
        )
        repository = data.get("repository") or {}
        can_view = bool(repository.get("viewerCanSeeIssueFields"))
        connection = repository.get("issueFields")
        if not connection:
            break
        fields.extend(
            _normalized_issue_field(field) for field in connection.get("nodes") or []
        )
        cursor = next_cursor(connection, cursor)
        if not cursor:
            break
    return can_view, fields


def set_issue_field_value(gitctx, issue_number, field_id, option_id=None):
    """Set or clear a single-select issue field and return normalized values.

    Generated-by: Cline
    """
    issue_id = issue_nodes(gitctx, [issue_number], "id", issue_only=True)[issue_number][
        "id"
    ]
    if option_id:
        query = SET_FIELD_VALUE
        variables = {
            "issueId": issue_id,
            "fieldId": field_id,
            "optionId": option_id,
        }
    else:
        query = DELETE_FIELD_VALUE
        variables = {"issueId": issue_id, "fieldId": field_id}
    data = execute(_post(gitctx), query, variables)
    payload = data.get("setIssueFieldValue") or {}
    issue = payload.get("issue") or {}
    connection = issue.get("issueFieldValues")
    if connection is None:
        return _normalized_field_values(payload.get("issueFieldValues"))
    return _normalized_field_values(connection.get("nodes"))


def enrich_issues(gitctx, issues):
    if not issues:
        return {}
    nodes = issue_nodes(
        gitctx,
        [i["number"] for i in issues],
        "id number " + PARENT + " " + LINKS + " " + FIELD_VALUES,
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
    for node in nodes.values():
        node["issue_field_values"] = _normalized_field_values(
            (node.get("issueFieldValues") or {}).get("nodes")
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
