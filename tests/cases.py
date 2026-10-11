"""Case set-ups shared by tests: the cleaned DISP-002 No-Show Dispute with its evidence sealed."""

from src.contracts import Case
from src.intake import load_catalog
from src.llm.stub import StubModel, load_replies
from src.store import CaseStore
from src.tools.evidence import gather_evidence

from tests.builders import a_submission

DISPUTE_ID = "DISP-002"


def a_sealed_no_show_case() -> tuple[CaseStore, Case]:
    catalog = load_catalog()
    dispute = catalog.dispute(DISPUTE_ID)
    store = CaseStore()
    case = store.create_case(dispute)
    store.add_evidence(case.case_id, gather_evidence(dispute.trip_id, catalog), agent="evidence")
    store.seal_evidence(case.case_id)
    return store, store.get_case(case.case_id)


def fixture_submissions():
    """One Submission per advocate, with markers so a test can tell whose text is whose."""
    rider = a_submission(
        author="rider_advocate",
        claim_restated="RIDER-MARKER: the driver was not at the pickup point.",
        policy_clause_ids=[],
    )
    driver = a_submission(
        author="driver_advocate",
        claim_restated="DRIVER-MARKER: the driver waited at the pickup point for the full window.",
        facts_relied_on=["EV-GPS-1", "EV-CHAT-1"],
        policy_clause_ids=[],
        requested_outcome="Uphold the no-show fee.",
    )
    return rider, driver


def stub_replies(dispute_id: str = DISPUTE_ID) -> dict:
    """The scripted replies for a prepared Dispute, keyed by agent."""
    return load_replies(dispute_id)


def a_stub_for(case_id: str, dispute_id: str = DISPUTE_ID) -> StubModel:
    return StubModel({(case_id, agent): reply for agent, reply in load_replies(dispute_id).items()})
