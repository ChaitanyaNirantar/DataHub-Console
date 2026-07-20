# Dataset Catalog: github_repos

- **Source:** GitHub Search API
- **Description:** Public GitHub repository metadata, sourced via the GitHub Search API.
- **Row count:** 60
- **Quarantined records:** 0
- **Primary key:** repo_id
- **Last updated (UTC):** 2026-07-17T22:59:46.504488+00:00

## Fields

| Field | Type | Nullable | Null rate |
|---|---|---|---|
| repo_id | int | False | 0.0 |
| full_name | str | False | 0.0 |
| description | str | True | 0.0 |
| language | str | True | 0.0 |
| stars | int | False | 0.0 |
| forks | int | False | 0.0 |
| open_issues | int | False | 0.0 |
| created_at | str | False | 0.0 |
| pushed_at | str | False | 0.0 |
| license | str | True | 0.0 |
| url | str | False | 0.0 |