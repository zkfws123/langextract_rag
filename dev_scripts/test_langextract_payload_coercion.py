"""Minimal regression checks for LangExtract output normalization.

Run directly with Python. It doesn't call external LLMs.
It validates that our patched parser helpers normalize various JSON shapes
into langextract's expected top-level {"extractions": [...]}.
"""

import json

from src.parsers.knowledge_extractor import _coerce_langextract_payload


def _as_obj(s: str):
    return json.loads(_coerce_langextract_payload(s))


def test_list_becomes_extractions():
    obj = _as_obj('[{"extraction_class":"实体","extraction_text":"张三","attributes":{}}]')
    assert "extractions" in obj
    assert isinstance(obj["extractions"], list)
    assert obj["extractions"][0]["extraction_text"] == "张三"


def test_alt_key_entities_mapped():
    obj = _as_obj('{"entities":[{"extraction_class":"实体","extraction_text":"清华大学","attributes":{}}]}')
    assert "extractions" in obj
    assert len(obj["extractions"]) == 1


def test_single_extraction_wrapped():
    obj = _as_obj('{"extraction_class":"实体","extraction_text":"北京大学","attributes":{}}')
    assert "extractions" in obj
    assert len(obj["extractions"]) == 1


def test_fenced_json_stripped_and_parsed():
    obj = _as_obj('```json\n{"extractions": []}\n```')
    assert "extractions" in obj
    assert obj["extractions"] == []


if __name__ == "__main__":
    # Simple runner
    test_list_becomes_extractions()
    test_alt_key_entities_mapped()
    test_single_extraction_wrapped()
    test_fenced_json_stripped_and_parsed()
    print("OK")
