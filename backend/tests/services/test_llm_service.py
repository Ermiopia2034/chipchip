import importlib
from types import SimpleNamespace


def test_tool_declarations_have_all_tools():
    mod = importlib.import_module("app.services.llm_service")
    decls = mod._tool_declarations()
    names = [d["name"] for d in decls]
    expected = [
        "search_products",
        "get_pricing_insights",
        "rag_query",
        "create_order",
        "add_inventory",
        "check_supplier_stock",
        "get_supplier_schedule",
        "suggest_flash_sale",
    ]
    assert names == expected


def test_llm_service_parses_tool_call(monkeypatch):
    # Ensure GEMINI key is set to avoid configure issues
    monkeypatch.setenv("GEMINI_API_KEY", "test")

    # Reload modules to pick new env
    config = importlib.import_module("app.config")
    importlib.reload(config)

    # Build fake response objects
    class FakePart:
        def __init__(self):
            self.function_call = SimpleNamespace(name="search_products", args={"query": "tomato"})

    class FakeContent:
        def __init__(self):
            self.parts = [FakePart()]

    class FakeCandidate:
        def __init__(self):
            self.content = FakeContent()

    class FakeResp:
        def __init__(self):
            self.candidates = [FakeCandidate()]

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, messages):
            return FakeResp()

    llm_mod = importlib.import_module("app.services.llm_service")

    # Monkeypatch genai symbols used inside module
    monkeypatch.setattr(llm_mod.genai, "GenerativeModel", FakeModel, raising=True)
    monkeypatch.setattr(llm_mod.genai, "configure", lambda **kwargs: None, raising=True)

    importlib.reload(llm_mod)
    svc = llm_mod.LLMService()
    out = svc.chat([{"role": "user", "content": "hi"}], tools=llm_mod._tool_declarations())
    assert out["type"] == "tool_call"
    assert out["name"] == "search_products"
    assert out["arguments"] == {"query": "tomato"}


def test_llm_service_parses_text(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    config = importlib.import_module("app.config")
    importlib.reload(config)

    class FakePartText:
        def __init__(self):
            self.text = "Hello there"
            self.function_call = None

    class FakeContentText:
        def __init__(self):
            self.parts = [FakePartText()]

    class FakeCandidateText:
        def __init__(self):
            self.content = FakeContentText()

    class FakeRespText:
        def __init__(self):
            self.candidates = [FakeCandidateText()]
            self.text = "Hello there"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, messages):
            return FakeRespText()

    llm_mod = importlib.import_module("app.services.llm_service")
    monkeypatch.setattr(llm_mod.genai, "GenerativeModel", FakeModel, raising=True)
    monkeypatch.setattr(llm_mod.genai, "configure", lambda **kwargs: None, raising=True)

    importlib.reload(llm_mod)
    svc = llm_mod.LLMService()
    out = svc.chat([{"role": "user", "content": "hi"}], tools=None)
    assert out["type"] == "text"
    assert out["content"] == "Hello there"

