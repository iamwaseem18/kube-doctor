"""Network checks: services without endpoints, ingress issues."""

import json

from kubernetes import client
from rich.console import Console
from rich.table import Table

console = Console()


def check_network(namespace=None, output_format="table"):
    """Check networking health.

    Checks for:
    - Services with no endpoints (dead services)
    - Services with mismatched selectors
    - Ingress resources with missing backends
    - LoadBalancer services without external IPs

    Returns a dict with 'issues' and 'warnings' counts.
    """
    v1 = client.CoreV1Api()
    networking_api = client.NetworkingV1Api()

    issues = []
    warnings = []

    # Get services
    if namespace:
        services = v1.list_namespaced_service(namespace)
    else:
        services = v1.list_service_for_all_namespaces()

    for svc in services.items:
        svc_name = svc.metadata.name
        svc_ns = svc.metadata.namespace

        # Skip headless and kubernetes services
        if svc.spec.cluster_ip == "None":
            continue
        if svc_name == "kubernetes" and svc_ns == "default":
            continue

        # Check for services without endpoints
        if svc.spec.selector:
            try:
                endpoints = v1.read_namespaced_endpoints(svc_name, svc_ns)
                has_ready = False
                if endpoints.subsets:
                    for subset in endpoints.subsets:
                        if subset.addresses:
                            has_ready = True
                            break

                if not has_ready:
                    issues.append({
                        "namespace": svc_ns,
                        "resource": f"service/{svc_name}",
                        "check": "No Ready Endpoints",
                        "detail": "Service has selectors but no ready endpoints",
                        "severity": "error",
                    })
            except client.exceptions.ApiException:
                issues.append({
                    "namespace": svc_ns,
                    "resource": f"service/{svc_name}",
                    "check": "Missing Endpoints",
                    "detail": "Could not find endpoints object for this service",
                    "severity": "error",
                })

        # Check LoadBalancer without external IP
        if svc.spec.type == "LoadBalancer":
            ingress_list = svc.status.load_balancer.ingress if svc.status.load_balancer else None
            if not ingress_list:
                warnings.append({
                    "namespace": svc_ns,
                    "resource": f"service/{svc_name}",
                    "check": "Pending LoadBalancer",
                    "detail": "LoadBalancer service has no external IP assigned",
                    "severity": "warning",
                })

    # Check ingress resources
    try:
        if namespace:
            ingresses = networking_api.list_namespaced_ingress(namespace)
        else:
            ingresses = networking_api.list_ingress_for_all_namespaces()

        for ing in ingresses.items:
            ing_name = ing.metadata.name
            ing_ns = ing.metadata.namespace

            if ing.spec.rules:
                for rule in ing.spec.rules:
                    if rule.http and rule.http.paths:
                        for path in rule.http.paths:
                            backend = path.backend
                            if backend.service:
                                backend_svc = backend.service.name
                                # Verify the backend service exists
                                try:
                                    v1.read_namespaced_service(backend_svc, ing_ns)
                                except client.exceptions.ApiException:
                                    issues.append({
                                        "namespace": ing_ns,
                                        "resource": f"ingress/{ing_name}",
                                        "check": "Missing Backend",
                                        "detail": f"Backend service '{backend_svc}' does not exist",
                                        "severity": "error",
                                    })

            # Check for missing TLS
            if ing.spec.tls is None and ing.spec.rules:
                hosts = [r.host for r in ing.spec.rules if r.host]
                if hosts:
                    warnings.append({
                        "namespace": ing_ns,
                        "resource": f"ingress/{ing_name}",
                        "check": "No TLS",
                        "detail": f"Ingress serves {', '.join(hosts[:3])} without TLS",
                        "severity": "warning",
                    })
    except client.exceptions.ApiException:
        pass

    # Output
    all_findings = issues + warnings

    if output_format == "json":
        console.print_json(json.dumps(all_findings, indent=2))
    else:
        console.print("\n[bold]Network Health Check[/bold]")
        if not all_findings:
            console.print("[green]  All network resources are healthy.[/green]")
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
