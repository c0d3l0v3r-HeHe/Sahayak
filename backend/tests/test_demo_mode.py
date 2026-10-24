from app.engine.playwright_engine import PlaywrightEngine
from app.flows.registry import FlowRegistry
from app.flows.runner import FlowRunner, RunnerConfig


def test_demo_mode_routes_to_mock_sites():
    flows = FlowRegistry.load()
    runner = FlowRunner(
        PlaywrightEngine(), RunnerConfig(demo_mode=True, mock_sites_url="http://api:8000/mock")
    )
    assert runner.base_url(flows.get("pnr_status")) == "http://api:8000/mock/pnr"
    assert runner.base_url(flows.get("scheme_finder")) == "http://api:8000/mock/myscheme"


def test_live_mode_uses_real_sites():
    flows = FlowRegistry.load()
    runner = FlowRunner(PlaywrightEngine(), RunnerConfig(demo_mode=False))
    assert (
        runner.base_url(flows.get("train_running_status"))
        == "https://enquiry.indianrail.gov.in/mntes"
    )
    assert runner.base_url(flows.get("scheme_finder")) == "https://www.myscheme.gov.in"
    assert runner.base_url(flows.get("pnr_status")) == "https://www.indianrail.gov.in/enquiry"


def test_verification_status_is_explicit():
    flows = {f.id: f for f in FlowRegistry.load().all()}
    for flow in flows.values():
        assert flow.notes, f"{flow.id} should document how its selectors were verified"
    # PNR could not be fully checked against the live site yet; it must say so.
    assert flows["pnr_status"].verified_at is None and "TODO" in flows["pnr_status"].notes
