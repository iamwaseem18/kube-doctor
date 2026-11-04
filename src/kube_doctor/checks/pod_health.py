"""Pod health checks: crashed, pending, restart-looping pods."""

import json

from kubernetes import client
from rich.console import Console
from rich.table import Table

console = Console()

RESTART_THRESHOLD = 5


def check_pods(namespace=None, output_format="table"):
    """Check all pods for health issues.

    Returns a dict with 'issues' and 'warnings' counts.
    """
    v1 = client.CoreV1Api()

    if namespace:
        pods = v1.list_namespaced_pod(namespace)
    else:
        pods = v1.list_pod_for_all_namespaces()

    issues = []
    warnings = []

    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_ns = pod.metadata.namespace
        phase = pod.status.phase

        # Pending pods
        if phase == "Pending":
            reasons = []
            if pod.status.conditions:
                for cond in pod.status.conditions:
                    if cond.status == "False" and cond.message:
                        reasons.append(cond.message)
            issues.append({
                "pod": pod_name,
                "namespace": pod_ns,
                "status": "Pending",
                "reason": "; ".join(reasons) if reasons else "Unknown",
                "severity": "error",
            })

        # Failed pods
        if phase == "Failed":
            reason = pod.status.reason or "Unknown"
            issues.append({
                "pod": pod_name,
                "namespace": pod_ns,
                "status": "Failed",
                "reason": reason,
                "severity": "error",
            })

        # Container-level checks
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                # CrashLoopBackOff
                if cs.state and cs.state.waiting:
                    if cs.state.waiting.reason in (
                        "CrashLoopBackOff",
                        "ImagePullBackOff",
                        "ErrImagePull",
                        "CreateContainerConfigError",
                    ):
                        issues.append({
                            "pod": pod_name,
                            "namespace": pod_ns,
                            "status": cs.state.waiting.reason,
                            "reason": cs.state.waiting.message or "N/A",
                            "severity": "error",
                        })

                # High restart count
                if cs.restart_count and cs.restart_count >= RESTART_THRESHOLD:
                    warnings.append({
                        "pod": pod_name,
                        "namespace": pod_ns,
                        "status": f"{cs.restart_count} restarts",
                        "reason": f"Container '{cs.name}' has restarted {cs.restart_count} times",
                        "severity": "warning",
                    })

    # Output
    all_findings = issues + warnings

    if output_format == "json":
        console.print_json(json.dumps(all_findings, indent=2))
    else:
        console.print("\n[bold]Pod Health Check[/bold]")
        if not all_findings:
            console.print("[green]  All pods are healthy.[/green]")
        else:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Namespace", style="cyan")
            table.add_column("Pod", style="white")
            table.add_column("Status", style="white")
            table.add_column("Reason")
            table.add_column("Severity")

            for f in all_findings:
                sev_style = "red" if f["severity"] == "error" else "yellow"
                table.add_row(
                    f["namespace"],
                    f["pod"],
                    f["status"],
                    f["reason"][:80],
                    f"[{sev_style}]{f['severity'].upper()}[/{sev_style}]",
                )
            console.print(table)

    return {"issues": len(issues), "warnings": len(warnings)}
