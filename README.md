# kube-doctor

[![CI](https://github.com/iamwaseem18/kube-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/iamwaseem18/kube-doctor/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A CLI tool for Kubernetes cluster health diagnostics. Quickly identify crashed pods, resource pressure, security misconfigurations, and networking issues across your cluster.

## Features

- **Pod Health** - Detect CrashLoopBackOff, pending pods, image pull errors, and high restart counts
- **Node Diagnostics** - Check node readiness, memory/disk/PID pressure, and scheduling taints
- **Security Audit** - Find privileged containers, pods running as root, missing network policies, and overly permissive RBAC bindings
- **Network Check** - Identify services without endpoints, pending LoadBalancers, missing ingress backends, and missing TLS
- **Full Scan** - Run all checks at once with a single command
- **Multiple Output Formats** - Human-readable tables (Rich) or JSON for automation

## Installation

```bash
pip install git+https://github.com/iamwaseem18/kube-doctor.git
```

Or clone and install locally:

```bash
git clone https://github.com/iamwaseem18/kube-doctor.git
cd kube-doctor
pip install -e .
```

## Usage

Make sure your `kubeconfig` is configured (or run inside a cluster).

### Full cluster scan

```bash
kube-doctor scan
```

### Check specific areas

```bash
# Pod health
kube-doctor pods

# Node conditions and resource pressure
kube-doctor nodes

# Security audit
kube-doctor security

# Network health
kube-doctor network
```

### Options

```bash
# Target a specific namespace
kube-doctor pods -n production

# JSON output for scripting
kube-doctor scan -o json

# Version
kube-doctor --version
```

### Sample Output

```
╭──────────── Cluster Scan ────────────╮
│   kube-doctor v0.1.0                 │
│   Running full cluster health scan...│
╰──────────────────────────────────────╯

Pod Health Check
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Namespace ┃ Pod          ┃ Status           ┃ Reason             ┃ Severity┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ default   │ api-server-1 │ CrashLoopBackOff │ Back-off restarting│ ERROR   │
│ monitoring│ prom-node-2  │ 12 restarts      │ Container 'exporte │ WARNING │
└───────────┴──────────────┴──────────────────┴────────────────────┴─────────┘

Node Health Check
  All nodes are healthy.

Security Audit
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Namespace ┃ Resource      ┃ Check            ┃ Detail            ┃ Severity┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ default   │ namespace/def │ No Network Polic │ Namespace has no  │ WARNING │
└───────────┴───────────────┴──────────────────┴───────────────────┴─────────┘

Scan complete: 1 issue(s), 2 warning(s)
```

## Development

```bash
git clone https://github.com/iamwaseem18/kube-doctor.git
cd kube-doctor
pip install -e ".[dev]"
pytest
```

## License

MIT
