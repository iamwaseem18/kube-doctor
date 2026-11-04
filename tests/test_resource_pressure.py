"""Tests for node resource pressure checks."""

from unittest.mock import MagicMock, patch

from kube_doctor.checks.resource_pressure import _parse_resource, check_nodes


def test_parse_cpu_millicores():
    assert _parse_resource("500m", "cpu") == 500
    assert _parse_resource("1", "cpu") == 1000
    assert _parse_resource("2", "cpu") == 2000


def test_parse_memory():
    assert _parse_resource("1Ki", "memory") == 1024
    assert _parse_resource("1Mi", "memory") == 1024**2
    assert _parse_resource("1Gi", "memory") == 1024**3


def _make_node(name, ready=True, conditions=None, taints=None):
    """Create a mock node object."""
    node = MagicMock()
    node.metadata.name = name
    node.spec.taints = taints or []

    if conditions is None:
        cond = MagicMock()
        cond.type = "Ready"
        cond.status = "True" if ready else "False"
        cond.message = "" if ready else "Node not ready"
        conditions = [cond]

    node.status.conditions = conditions
    node.status.allocatable = {"cpu": "3800m", "memory": "15Gi"}
    node.status.capacity = {"cpu": "4000m", "memory": "16Gi"}
    return node


@patch("kube_doctor.checks.resource_pressure.client")
def test_healthy_nodes(mock_client):
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    nodes = MagicMock()
    nodes.items = [_make_node("node-1")]
    mock_v1.list_node.return_value = nodes

    result = check_nodes(output_format="json")
    assert result["issues"] == 0


@patch("kube_doctor.checks.resource_pressure.client")
def test_not_ready_node(mock_client):
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1

    nodes = MagicMock()
    nodes.items = [_make_node("bad-node", ready=False)]
    mock_v1.list_node.return_value = nodes

    result = check_nodes(output_format="json")
    assert result["issues"] == 1
