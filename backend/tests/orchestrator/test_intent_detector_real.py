import os
import pytest


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_intent_detector_flash_model():
    from app.orchestrator.intent_detector import IntentDetector

    det = IntentDetector(model="models/gemini-flash-latest")

    out1 = det.detect("I want to add 50kg tomatoes at 55 birr per kg")
    assert out1["intent"] in ("add_inventory",)

    out2 = det.detect("How to store avocados?")
    assert out2["intent"] in ("knowledge_query",)

    out3 = det.detect("Show my inventory")
    assert out3["intent"] in ("check_stock", "product_inquiry")

