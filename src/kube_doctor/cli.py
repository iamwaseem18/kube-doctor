"""CLI entry point for kube-doctor."""

import sys

import click
from rich.console import Console
from rich.panel import Panel

from kube_doctor import __version__
from kube_doctor.checks.pod_health import check_pods
from kube_doctor.checks.resource_pressure import check_nodes
from kube_doctor.checks.security_audit import check_security
from kube_doctor.checks.networking import check_network

console = Console()


def _load_kube_config():
    """Load Kubernetes configuration."""
    from kubernetes import config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        try:
            config.load_kube_config()
        except config.ConfigException:
            console.print(
                "[bold red]Error:[/] Cannot connect to Kubernetes cluster.\n"
                "Make sure your kubeconfig is set up or you're running inside a cluster."
            )
            sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="kube-doctor")
def cli():
    """Kubernetes cluster health diagnostics.

    Run health checks against your Kubernetes cluster to find
    crashed pods, resource pressure, security issues, and networking
    problems.
    """
    pass


@cli.command()
@click.option("-n", "--namespace", default=None, help="Target namespace (default: all).")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table", help="Output format.")
def scan(namespace, output):
    """Run a full cluster health scan."""
    _load_kube_config()
    console.print(
        Panel(
            f"[bold blue]kube-doctor v{__version__}[/bold blue]\n"
            "Running full cluster health scan...",
            title="Cluster Scan",
            border_style="blue",
        )
    )
    results = {}
    results["pods"] = check_pods(namespace=namespace, output_format=output)
    results["nodes"] = check_nodes(output_format=output)
    results["security"] = check_security(namespace=namespace, output_format=output)
    results["network"] = check_network(namespace=namespace, output_format=output)

    total_issues = sum(r.get("issues", 0) for r in results.values())
    total_warnings = sum(r.get("warnings", 0) for r in results.values())

    if total_issues == 0 and total_warnings == 0:
        console.print("\n[bold green]All checks passed. Cluster looks healthy.[/bold green]")
    else:
        console.print(
            f"\n[bold yellow]Scan complete:[/bold yellow] "
            f"[red]{total_issues} issue(s)[/red], "
            f"[yellow]{total_warnings} warning(s)[/yellow]"
        )


@cli.command()
@click.option("-n", "--namespace", default=None, help="Target namespace (default: all).")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table", help="Output format.")
def pods(namespace, output):
    """Check pod health: crashes, restarts, pending pods."""
    _load_kube_config()
    check_pods(namespace=namespace, output_format=output)


@cli.command()
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table", help="Output format.")
def nodes(output):
    """Check node conditions and resource pressure."""
    _load_kube_config()
    check_nodes(output_format=output)


@cli.command()
@click.option("-n", "--namespace", default=None, help="Target namespace (default: all).")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table", help="Output format.")
def security(namespace, output):
    """Audit RBAC, root containers, and network policies."""
    _load_kube_config()
    check_security(namespace=namespace, output_format=output)


@cli.command()
@click.option("-n", "--namespace", default=None, help="Target namespace (default: all).")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table", help="Output format.")
def network(namespace, output):
    """Check services, endpoints, and ingress configuration."""
    _load_kube_config()
    check_network(namespace=namespace, output_format=output)


if __name__ == "__main__":
    cli()
