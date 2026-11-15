"""Deterministic mission scenario scheduling from explicitly user-supplied inputs."""
from __future__ import annotations
from collections import defaultdict, deque


def plan_scenario(activities: list[dict], resource_limits: dict[str, float]) -> dict:
    by_id={a["id"]:a for a in activities}
    if len(by_id) != len(activities): raise ValueError("activity IDs must be unique")
    if not activities: raise ValueError("at least one activity is required")
    indegree={k:0 for k in by_id}; children=defaultdict(list)
    for a in activities:
        for dep in a["depends_on"]:
            if dep not in by_id: raise ValueError(f"{a['id']}: unknown dependency {dep}")
            if dep == a["id"]: raise ValueError(f"{a['id']}: activity cannot depend on itself")
            indegree[a["id"]]+=1; children[dep].append(a["id"])
    queue=deque(sorted(k for k,v in indegree.items() if v==0)); order=[]
    while queue:
        node=queue.popleft(); order.append(node)
        for child in sorted(children[node]):
            indegree[child]-=1
            if indegree[child]==0: queue.append(child)
    if len(order)!=len(by_id): raise ValueError("dependency cycle detected")
    schedule={}; resource_issues=[]
    for ident in order:
        a=by_id[ident]
        start=max((schedule[d]["finish_hour"] for d in a["depends_on"]),default=0.0)
        finish=start+a["duration_hours"]
        schedule[ident]={"activity_id":ident,"name":a["name"],"start_hour":start,"finish_hour":finish,
                         "duration_hours":a["duration_hours"],"depends_on":a["depends_on"],"resources":a["resources"]}
        for resource, amount in a["resources"].items():
            if resource not in resource_limits:
                resource_issues.append({"activity_id":ident,"resource":resource,"status":"unknown","reason":"No capacity limit configured"})
            elif amount > resource_limits[resource]:
                resource_issues.append({"activity_id":ident,"resource":resource,"status":"exceeds-capacity",
                                        "demand":amount,"capacity":resource_limits[resource]})
    return {"schedule":[schedule[k] for k in order], "duration_hours":max(x["finish_hour"] for x in schedule.values()),
            "resource_issues":resource_issues,
            "status":"resource-constrained" if any(x["status"]=="exceeds-capacity" for x in resource_issues) else
                     ("resource-unknown" if resource_issues else "scheduled"),
            "method":"Dependency-based earliest-start schedule; durations and resource quantities are user inputs, not empirical predictions."}
