"""Security audit checks: RBAC, root containers, network policies."""

import json

from kubernetes import client
from rich.console import Console
from rich.table import Table

console = Console()


def check_security(namespace=None, output_format="table"):
    """Audit cluster security posture.

    Checks for:
    - Pods running as root
    - Containers with privileged mode
    - Missing network policies
    - Overly permissive RBAC bindings

    Returns a dict with 'issues' and 'warnings' counts.
    """
    v1 = client.CoreV1Api()
    rbac = client.RbacAuthorizationV1Api()
    networking = client.NetworkingV1Api()

    issues = []
    warnings = []

    # Check pods running as root or privileged
    if namespace:
        pods = v1.list_namespaced_pod(namespace)
    else:
        pods = v1.list_pod_for_all_namespaces()

    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_ns = pod.metadata.namespace

        if pod.spec.containers:
            for container in pod.spec.containers:
                sc = container.security_context

                # Privileged container
                if sc and sc.privileged:
                    issues.append({
                        "namespace": pod_ns,
                        "resource": f"pod/{pod_name}",
                        "check": "Privileged Container",
                        "detail": f"Container '{container.name}' runs in privileged mode",
                        "severity": "error",
                    })

                # Running as root
                if sc and sc.run_as_user == 0:
                    warnings.append({
                        "namespace": pod_ns,
                        "resource": f"pod/{pod_name}",
                        "check": "Root User",
                        "detail": f"Container '{container.name}' runs as UID 0 (root)",
                        "severity": "warning",
                    })

                # No security context at all
                if sc is None:
                    pod_sc = pod.spec.security_context
                    if pod_sc is None or (pod_sc.run_as_non_root is None and pod_sc.run_as_user is None):
                        warnings.append({
                            "namespace": pod_ns,
                            "resource": f"pod/{pod_name}",
                            "check": "No Security Context",
                            "detail": f"Container '{container.name}' has no security context defined",
                            "severity": "warning",
                        })

    # Check for namespaces without network policies
    namespaces = v1.list_namespace()
    system_ns = {"kube-system", "kube-public", "kube-node-lease"}

    for ns in namespaces.items:
        ns_name = ns.metadata.name
        if ns_name in system_ns:
            continue
        if namespace and ns_name != namespace:
            continue

        try:
            net_pols = networking.list_namespaced_network_policy(ns_name)
            if not net_pols.items:
                warnings.append({
                    "namespace": ns_name,
                    "resource": f"namespace/{ns_name}",
                    "check": "No Network Policies",
                    "detail": "Namespace has no network policies - all traffic is allowed",
                    "severity": "warning",
                })
        except client.exceptions.ApiException:
            pass

    # Check for overly permissive ClusterRoleBindings
    try:
        crbs = rbac.list_cluster_role_binding()
        for crb in crbs.items:
            if crb.role_ref.name == "cluster-admin":
                # Skip default system bindings
                if crb.metadata.name in ("cluster-admin", "system:masters"):
                    continue
                subjects_str = ""
                if crb.subjects:
                    subjects_str = ", ".join(
                        f"{s.kind}/{s.name}" for s in crb.subjects[:3]
                    )
                issues.append({
                    "namespace": "*",
                    "resource": f"clusterrolebinding/{crb.metadata.name}",
                    "check": "cluster-admin Binding",
                    "detail": f"Grants cluster-admin to: {subjects_str}",
                    "severity": "error",
                })
    except client.exceptions.ApiException:
        pass

    # Output
    all_findings = issues + warnings

    if output_format == "json":
        console.print_json(json.dumps(all_findings, indent=2))
    else:
        console.print("\n[bold]Security Audit[/bold]")
        if not all_findings:
            console.print("[green]  No security issues found.[/green]")
        else:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Namespace", style="cyan")
            table.add_column("Resource", style="white")
            table.add_column("Check", style="white")
            table.add_column("Detail")
            table.add_column("Severity")

            for f in all_findings:
                sev_style = "red" if f["severity"] == "error" else "yellow"
                table.add_row(
                    f["namespace"],
                    f["resource"],
                    f["check"],
                    f["detail"][:70],
                    f"[{sev_style}]{f['severity'].upper()}[/{sev_style}]",
                )
            console.print(table)

    return {"issues": len(issues), "warnings": len(warnings)}
