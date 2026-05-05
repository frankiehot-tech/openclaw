from __future__ import annotations

from athena.semantic_layer.infra.tokenizer import (
    Tokenizer,
    count_tokens,
    token_budget_remaining,
)


class TestTokenizer:
    def test_count_empty(self):
        tk = Tokenizer()
        assert tk.count("") == 0

    def test_count_simple(self):
        tk = Tokenizer()
        assert tk.count("hello world") > 0

    def test_count_consistency(self):
        tk = Tokenizer()
        text = "Hello world this is a test"
        assert tk.count(text) == tk.count(text)

    def test_truncate_no_truncation(self):
        tk = Tokenizer()
        text = "hello world"
        result = tk.truncate(text, max_tokens=100)
        assert result == text

    def test_truncate_with_truncation(self):
        tk = Tokenizer()
        text = "hello world " * 50
        result = tk.truncate(text, max_tokens=10, suffix="...")
        assert len(result) < len(text)
        assert result.endswith("...")


class TestCountTokensHelper:
    def test_same_as_tokenizer(self):
        text = "hello world test"
        tk = Tokenizer()
        assert count_tokens(text) == tk.count(text)

    def test_with_model(self):
        text = "hello world"
        assert count_tokens(text, model="gpt-4o") > 0


class TestTokenBudgetRemaining:
    def test_normal_case(self):
        assert token_budget_remaining(50000, 30000, 5000) == 15000

    def test_consumed_all(self):
        assert token_budget_remaining(50000, 50000, 0) == 0

    def test_clamped_to_zero(self):
        assert token_budget_remaining(100, 200, 0) == 0

    def test_zero_total(self):
        assert token_budget_remaining(0, 0, 0) == 0
