"""Node resource pressure and condition checks."""

import json

from kubernetes import client
from rich.console import Console
from rich.table import Table

console = Console()

CPU_WARN_PERCENT = 80
MEMORY_WARN_PERCENT = 85


def _parse_resource(value, resource_type="cpu"):
    """Parse Kubernetes resource strings into comparable numbers."""
    if value is None:
        return 0
    if resource_type == "cpu":
        if value.endswith("m"):
            return int(value[:-1])
        if value.endswith("n"):
            return int(value[:-1]) / 1_000_000
        return int(float(value) * 1000)
    else:  # memory
        multipliers = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}
        for suffix, mult in multipliers.items():
            if value.endswith(suffix):
                return int(value[: -len(suffix)]) * mult
        return int(value)


def check_nodes(output_format="table"):
    """Check node conditions and resource utilization.

    Returns a dict with 'issues' and 'warnings' counts.
    """
    v1 = client.CoreV1Api()
    nodes = v1.list_node()

    issues = []
    warnings = []

    for node in nodes.items:
        node_name = node.metadata.name

        # Check node conditions
        if node.status.conditions:
            for cond in node.status.conditions:
                if cond.type == "Ready" and cond.status != "True":
                    issues.append({
                        "node": node_name,
                        "check": "NotReady",
                        "detail": cond.message or "Node is not ready",
                        "severity": "error",
                    })
                elif cond.type in ("MemoryPressure", "DiskPressure", "PIDPressure") and cond.status == "True":
                    issues.append({
                        "node": node_name,
                        "check": cond.type,
                        "detail": cond.message or f"{cond.type} detected",
                        "severity": "error",
                    })

        # Check resource usage
        allocatable = node.status.allocatable or {}
        capacity = node.status.capacity or {}

        alloc_cpu = _parse_resource(allocatable.get("cpu", "0"), "cpu")
        cap_cpu = _parse_resource(capacity.get("cpu", "0"), "cpu")
        alloc_mem = _parse_resource(allocatable.get("memory", "0"), "memory")
        cap_mem = _parse_resource(capacity.get("memory", "0"), "memory")

        if cap_cpu > 0:
            reserved_cpu_pct = ((cap_cpu - alloc_cpu) / cap_cpu) * 100
            if reserved_cpu_pct > (100 - CPU_WARN_PERCENT):
                warnings.append({
                    "node": node_name,
                    "check": "CPU Reserved",
                    "detail": f"{reserved_cpu_pct:.0f}% of CPU capacity reserved by system",
                    "severity": "warning",
                })

        if cap_mem > 0:
            reserved_mem_pct = ((cap_mem - alloc_mem) / cap_mem) * 100
            if reserved_mem_pct > (100 - MEMORY_WARN_PERCENT):
                warnings.append({
                    "node": node_name,
                    "check": "Memory Reserved",
                    "detail": f"{reserved_mem_pct:.0f}% of memory capacity reserved by system",
                    "severity": "warning",
                })

        # Check for taints
        if node.spec.taints:
            unschedulable = [
                t for t in node.spec.taints
                if t.effect in ("NoSchedule", "NoExecute") and t.key != "node-role.kubernetes.io/master"
                and t.key != "node-role.kubernetes.io/control-plane"
            ]
            if unschedulable:
                taint_str = ", ".join(f"{t.key}={t.value}:{t.effect}" for t in unschedulable)
                warnings.append({
                    "node": node_name,
                    "check": "Taints",
                    "detail": f"Node has scheduling restrictions: {taint_str}",
                    "severity": "warning",
                })

    # Output
    all_findings = issues + warnings

    if output_format == "json":
        console.print_json(json.dumps(all_findings, indent=2))
    else:
        console.print("\n[bold]Node Health Check[/bold]")
        if not all_findings:
            console.print("[green]  All nodes are healthy.[/green]")
        else:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Node", style="cyan")
            table.add_column("Check", style="white")
            table.add_column("Detail")
            table.add_column("Severity")

            for f in all_findings:
                sev_style = "red" if f["severity"] == "error" else "yellow"
                table.add_row(
                    f["node"],
                    f["check"],
                    f["detail"][:80],
                    f"[{sev_style}]{f['severity'].upper()}[/{sev_style}]",
                )
            console.print(table)

    return {"issues": len(issues), "warnings": len(warnings)}
