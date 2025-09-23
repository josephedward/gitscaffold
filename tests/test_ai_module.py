import json
import types
import pytest

from scaffold import ai as ai_mod


def _fake_openai_response(text: str):
    class _Msg:
        def __init__(self, content):
            self.content = content
    class _Choice:
        def __init__(self, content):
            self.message = _Msg(content)
    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]
    return _Resp(text)


def test_extract_issues_openai_success(tmp_path, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("Some project notes")

    class FakeChat:
        def __init__(self):
            self.completions = types.SimpleNamespace(
                create=lambda **kwargs: _fake_openai_response(
                    """```json
                    [
                      {"title": "# Issue A", "description": "Desc A", "labels": ["bug"]},
                      {"title": "Issue B", "description": "Desc B"}
                    ]
                    ```"""
                )
            )

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr(ai_mod, "OpenAI", FakeOpenAI)

    issues = ai_mod.extract_issues_from_markdown(str(md), provider="openai", api_key="k")
    assert len(issues) == 2
    # Leading '#' is stripped
    assert issues[0]["title"] == "Issue A"
    assert issues[0]["description"] == "Desc A"
    assert issues[0]["labels"] == ["bug"]


def test_extract_issues_gemini_success(tmp_path, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("Notes for gemini")

    class FakeModel:
        def generate_content(self, prompt):
            class R:
                text = json.dumps([
                    {"title": "Item 1", "description": "Body"}
                ])
            return R()

    fake_genai = types.SimpleNamespace(
        GenerativeModel=lambda name: FakeModel(),
        configure=lambda api_key=None: None
    )
    monkeypatch.setattr(ai_mod, "genai", fake_genai)

    issues = ai_mod.extract_issues_from_markdown(str(md), provider="gemini", api_key="k")
    assert len(issues) == 1
    assert issues[0]["title"] == "Item 1"


def test_extract_issues_missing_key_raises(tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("Anything")
    with pytest.raises(ValueError):
        ai_mod.extract_issues_from_markdown(str(md), provider="openai", api_key="")


def test_extract_issues_bad_json_raises(tmp_path, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("Notes")

    class FakeChat:
        def __init__(self):
            self.completions = types.SimpleNamespace(
                create=lambda **kwargs: _fake_openai_response("not json at all")
            )

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr(ai_mod, "OpenAI", FakeOpenAI)

    with pytest.raises(ValueError):
        ai_mod.extract_issues_from_markdown(str(md), provider="openai", api_key="k")


def test_enrich_openai_success(monkeypatch):
    class FakeChat:
        def __init__(self):
            self.completions = types.SimpleNamespace(
                create=lambda **kwargs: _fake_openai_response("Enriched content\n\n- A\n- B")
            )

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr(ai_mod, "OpenAI", FakeOpenAI)

    enriched = ai_mod.enrich_issue_description(
        title="T", existing_body="old", provider="openai", api_key="k"
    )
    assert "Enriched content" in enriched


def test_enrich_openai_error_returns_existing(monkeypatch):
    class FakeErr(Exception):
        pass

    class FakeChat:
        def __init__(self):
            def raise_it(**kwargs):
                raise FakeErr("boom")
            self.completions = types.SimpleNamespace(create=raise_it)

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    # Map OpenAIError to our FakeErr so except branch matches
    monkeypatch.setattr(ai_mod, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(ai_mod, "OpenAIError", FakeErr)

    enriched = ai_mod.enrich_issue_description(
        title="T", existing_body="keep-this", provider="openai", api_key="k"
    )
    assert enriched == "keep-this"


def test_enrich_gemini_success(monkeypatch):
    class FakeModel:
        def generate_content(self, prompt):
            class R:
                text = "Gemini enriched body"
            return R()

    fake_genai = types.SimpleNamespace(
        GenerativeModel=lambda name: FakeModel(),
        configure=lambda api_key=None: None
    )
    monkeypatch.setattr(ai_mod, "genai", fake_genai)

    enriched = ai_mod.enrich_issue_description(
        title="T", existing_body="old", provider="gemini", api_key="k"
    )
    assert enriched.startswith("Gemini enriched")


def test_enrich_gemini_error_returns_existing(monkeypatch):
    class FakeModel:
        def generate_content(self, prompt):
            raise RuntimeError("fail")

    fake_genai = types.SimpleNamespace(
        GenerativeModel=lambda name: FakeModel(),
        configure=lambda api_key=None: None
    )
    monkeypatch.setattr(ai_mod, "genai", fake_genai)

    enriched = ai_mod.enrich_issue_description(
        title="T", existing_body="fallback", provider="gemini", api_key="k"
    )
    assert enriched == "fallback"

