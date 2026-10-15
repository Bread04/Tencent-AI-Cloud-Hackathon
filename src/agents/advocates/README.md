# Advocate implementation

The executable Rider and Driver Advocate lives in [`__init__.py`](__init__.py). The orchestrator calls both advocates with the same sealed Case snapshot, and neither receives the other party's Submission. The model returns a structured Submission; code validates its author, required counter-argument, and citations before the Case is stored.

The adjacent role files (`rider-advocate.md`, `driver-advocate.md`, and the Evidence/Policy Agent notes) are planning and prompt-design documents. They are not loaded by the running application. The implementation and its current stage order are documented in [the architecture guide](../../../docs/architecture.md); the product flow is in [the project README](../../../README.md) and the [demo script](../../../docs/demo-script.md).
