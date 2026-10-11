# Evidence analysis

Self-declared Hub metadata snapshot; downloads are not unique users and selected models are not a population sample.

`python analysis/build.py` rebuilds the committed outputs without a database server, network or API key. The build validates domains and observation counts before running `questions.sql`. The manifest records SHA-256 input and query hashes. SQL uses explicit denominators and window functions where useful. Outputs are descriptive summaries, not new causal or user-adoption evidence.

Grain: `model,root,downloads,depth,root_resolved,cycle`. Primary and unique keys in `build.py` identify observations; repeated references in citeaudit are retained because the grain is a reference check. Missing values fail ingestion instead of becoming zeros.
