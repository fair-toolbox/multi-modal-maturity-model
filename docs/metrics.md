# Metrics

This tool collects metrics from various sources to help you assess the maturity and quality of your research software.

## Overview

| Metric | Purpose | Data Source | Authentication |
|-----------|---------|-------------|----------------|
| **Repository** | Repository health metrics | GitHub/GitLab API | Required (token) |
| **Publication** | Citation metrics | Europe PMC API, Semantic Scholar API | Not required |
| **Fairness** | FAIR compliance | howfairis library | Not required |
| **Registry** | Tool metadata | bio.tools API | Not required |
| **Code Quality** | Code quality metrics | Lizard static analysis | Not required |


# Dimensions

## Compatibility

**Data sources:** bio.tools, GitHub/GitLab

**Metrics:**
- EDAM compatibility
- Workflow support
- Distribution support


## Fairness

**Data sources:** howfairis, EuropePMC (publication open access)

**Metrics:**
- Has open repository
- Has license
- Has registry (badge)
- Has ciatation file or zenodo badge
- Checklist: has core infrastructures badge


## Maintainability

**Data Sources:** Lizard, GitHub/GitLab

**Metrics:**
- Total nloc
- Total CCN
- Average CCN
- Duplicate rate
- Has old languages


## Scientific Impact

**Data sources:** EuropePMC, Semantic Scholar

**Metrics:**
- Citation count
- Influential citation count


## Security

Security checks for protected branches and presence of security policies, and security scanning workflows.

**Data sources:** GitHub/GitLab

**Metrics:**
- Default branch protected
- Has security policy
- Has security scanning


## Sustainability

Sustainability combines repository activity and maintenance resilience signals from GitHub or GitLab.

**Data sources:** GitHub/GitLab

**Metrics:**
- Average issue close time
- Number of open issues
- Days since last commit
- Contributor diversity measured with the Inverse Simpson index on commit shares
