---
name: Pub/Sub Subscription Request
about: Request to onboard a new consumer for repository data.
title: "[Pub/Sub Subscription]"
labels: bap
assignees: ''
type: Feature

---

### Subscription Request Details

Please provide the details below to onboard as a consumer. Our platform will manage the subscription resources (Dead Letter Queues, retention policies, etc.).

**1. Repository Name**
<!-- The full repository name including the owner/organization (e.g., google/jax) -->
[Enter repository name here]

**2. Principal**
<!-- The service account email that will consume the data (e.g., my-dashboard-sa@my-project.iam.gserviceaccount.com) -->
[Enter service account email here]

**3. Data Sensitivity**
<!-- All benchmarks run via this platform are published to a single shared public topic by default. If your data cannot be made public (e.g., private repo), specify that you require a private topic. -->
[Public / Private]
