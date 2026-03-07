# Metrics

This tool collects metrics from various sources to help you assess the maturity and quality of your research software. M4 gathers data about repository activity, code quality, FAIR compliance, citations, and more.

## Overview

| Metric | Purpose | Data Source | Authentication |
|-----------|---------|-------------|----------------|
| **Repository** | Repository health metrics | GitHub/GitLab API | Required (token) |
| **Publication** | Citation metrics | Europe PMC API | Not required |
| **Fairness** | FAIR compliance | howfairis library | Not required |
| **Registry** | Tool metadata | bio.tools API | Not required |
| **Code Quality** | Code quality metrics | Lizard static analysis | Not required |

## Repository Metrics

Collected from repository providers (GitHub or GitLab).

- **Repository statistics**: Stars, forks, watchers, size
- **Activity metrics**: Open/closed issues, pull requests
- **Maintenance indicators**: Last commit date, update frequency
- **Community metrics**: Contributors, issue resolution time
- **Documentation**: README presence, wiki status

## Publication Metrics

Collected from the EuropePMC API.

- **Citation counts**
- **Open access status**

## Fairness

howfairis

## Registry

bio.tools

## Code Quality
