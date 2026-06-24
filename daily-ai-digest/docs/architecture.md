# Architecture

The pipeline stages are collect, extract, normalize, deduplicate, filter, cluster, translate, summarize, render, and deliver. Each stage commits JSON state under `data/state/runs/<run_id>/stages/`. A repeated completed `run_id` returns the stored report and does not recollect or redeliver.
