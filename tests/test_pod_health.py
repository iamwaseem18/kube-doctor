"""Tests for pod health checks."""

from unittest.mock import MagicMock, patch

from kube_doctor.checks.pod_health import check_pods


def _make_pod(name, namespace, phase, containers=None):
    """Create a mock pod object."""
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.namespace = namespace
    pod.status.phase = phase
    pod.status.conditions = []
    pod.status.container_statuses = containers or []
    return pod


def _make_container_status(name, restart_count=0, waiting_reason=None, waiting_message=None):
    """Create a mock container status."""
    cs = MagicMock()
    cs.name = name
    cs.restart_count = restart_count
    if waiting_reason:
        cs.state.waiting.reason = waiting_reason
        cs.state.waiting.message = waiting_message
    else:
        cs.state.waiting = None
    return cs


@patch("kube_doctor.checks.pod_health.client")
def test_healthy_pods(mock_client):
    """All pods running should return zero issues."""
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    pods = MagicMock()
    pods.items = [
        _make_pod("web-1", "default", "Running"),
        _make_pod("api-1", "default", "Running"),
    ]
    mock_v1.list_pod_for_all_namespaces.return_value = pods

    result = check_pods(output_format="json")
    assert result["issues"] == 0
    assert result["warnings"] == 0


@patch("kube_doctor.checks.pod_health.client")
def test_pending_pod(mock_client):
    """A pending pod should be flagged as an issue."""
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    pods = MagicMock()
    pods.items = [_make_pod("stuck-pod", "default", "Pending")]
    mock_v1.list_pod_for_all_namespaces.return_value = pods

    result = check_pods(output_format="json")
    assert result["issues"] == 1


@patch("kube_doctor.checks.pod_health.client")
def test_crashloop_pod(mock_client):
    """A CrashLoopBackOff container should be flagged."""
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    cs = _make_container_status("app", waiting_reason="CrashLoopBackOff", waiting_message="Back-off restarting")
    pods = MagicMock()
    pods.items = [_make_pod("crash-pod", "default", "Running", containers=[cs])]
    mock_v1.list_pod_for_all_namespaces.return_value = pods

    result = check_pods(output_format="json")
    assert result["issues"] == 1


@patch("kube_doctor.checks.pod_health.client")
def test_high_restart_count(mock_client):
    """High restart count should produce a warning."""
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    cs = _make_container_status("app", restart_count=10)
    pods = MagicMock()
    pods.items = [_make_pod("restart-pod", "default", "Running", containers=[cs])]
    mock_v1.list_pod_for_all_namespaces.return_value = pods

    result = check_pods(output_format="json")
    assert result["warnings"] == 1


@patch("kube_doctor.checks.pod_health.client")
def test_namespace_filter(mock_client):
    """Namespace filter should use list_namespaced_pod."""
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    pods = MagicMock()
    pods.items = []
    mock_v1.list_namespaced_pod.return_value = pods

    check_pods(namespace="prod", output_format="json")
    mock_v1.list_namespaced_pod.assert_called_once_with("prod")
