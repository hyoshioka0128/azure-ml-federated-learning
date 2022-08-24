# Federated Learning in Azure ML

> :warning: Need to update this README!

**Disclaimer:** this repo is examples + recipes only, and none of this has SLAs on support or correctness.

Although there is no specific commitment to a timeline yet, Azure ML is working on first-class support for cross-silo federated learning. Cross-silo federated learning allows data scientists to run pipelines against data in multiple isolated silos, with the platform guaranteeing that only approved and policy-compliant jobs transfer "safe" data across silo boundaries. Here a "silo" means an "isolated" collection of storage and compute. And "isolated" means that the platform guarantees:
- only compute within the silo can "touch" storage within the silo;
- only data of public or system metadata classification can be moved outside the silo;
- only "approved" jobs can change the classification of data or move it outside the silo.

Silos are expected to be reliable (i.e., no concerns around network connectivity or uptime). We also assume a hard cap of **≤ 100 silos**.

Current contents:
- `mlops`: a collection of resources to automatically provision the orchestrator and silos resources.
- `examples`: simple example of using shrike Federated Learning API + Arc + Kubernetes + Azure ML to submit a Federated Learning experiment.
- `docs`: generic plan for a company to onboard to Federated Learning through Azure ML.

More details, recipes, and examples coming soon!
