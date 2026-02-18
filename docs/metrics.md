# Metrics

TBD


## Overview

| Collector | Purpose | Data Source | Authentication |
|-----------|---------|-------------|----------------|
| **GitHubCollector** | Repository health metrics | GitHub API | Required (token) |
| **EuropePMCCollector** | Citation metrics | Europe PMC API | Not required |
| **FairnessCollector** | FAIR compliance | howfairis library | Not required |
| **BioToolsCollector** | Tool metadata | bio.tools API | Not required |
| **CodeQualityCollector** | Code quality metrics | Lizard static analysis | Not required |

## GitHubCollector

- **Repository statistics**: Stars, forks, watchers, size
- **Activity metrics**: Open/closed issues, pull requests
- **Maintenance indicators**: Last commit date, update frequency
- **Community metrics**: Contributors, issue resolution time
- **Documentation**: README presence, wiki status


## EuropePMCCollector

Collects citation metrics and publication information from Europe PMC.

- **Citation counts**
- **Open access status**

## FairnessCollector

howfairis

## BioToolsCollector
