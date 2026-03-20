"""Tests for concept alias matching and graph traversal.

Tests the full get_concept_context pipeline against the seeded Kuzu graph.
Requires the graph to be seeded before running (data/kuzu/ must exist).
"""

from __future__ import annotations

import pytest
from services.pipeline.src.graph.traversal import get_concept_context


@pytest.fixture(scope="module")
def ctx():
    """Helper to call get_concept_context and return results."""

    def _ctx(query: str) -> dict:
        return get_concept_context(query)

    return _ctx


class TestConceptMatching:
    """Verify that common natural-language queries match the right concepts."""

    def test_peace_matches_shanti(self, ctx):
        result = ctx("What is the path to inner peace?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Shanti" in names

    def test_anger_matches_krodha(self, ctx):
        result = ctx("How do I deal with anger?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Krodha" in names

    def test_desire_matches_kama(self, ctx):
        result = ctx("What does the Gita say about desire?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Kama" in names

    def test_mind_matches_manas(self, ctx):
        result = ctx("How to control the mind?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Manas" in names

    def test_death_matches_atman(self, ctx):
        result = ctx("What is the meaning of death?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Atman" in names

    def test_happiness_matches_samata(self, ctx):
        result = ctx("How to find happiness?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Samata" in names

    def test_anxious_matches_manas(self, ctx):
        result = ctx("What should I do when I feel anxious?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Manas" in names

    def test_grief_matches_vairagya(self, ctx):
        result = ctx("How to deal with grief and loss?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Vairagya" in names

    def test_work_matches_karma_yoga(self, ctx):
        result = ctx("What does the Gita say about work?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Karma Yoga" in names

    def test_nonviolence_matches_ahimsa(self, ctx):
        result = ctx("What is non-violence in the Gita?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Ahimsa" in names


class TestGraphExpansion:
    """Verify that matched concepts expand to related concepts and key verses."""

    def test_peace_expands_to_related(self, ctx):
        result = ctx("What is the path to inner peace?")
        related = {c["name"] for c in result["related_concepts"]}
        assert "Sthitaprajna" in related or "Dhyana" in related

    def test_anger_expands_to_desire(self, ctx):
        result = ctx("How do I deal with anger?")
        related = {c["name"] for c in result["related_concepts"]}
        assert "Kama" in related

    def test_matched_concepts_have_key_verses(self, ctx):
        result = ctx("What does the Gita say about desire?")
        assert len(result["key_verses"]) > 0

    def test_graph_context_is_nonempty(self, ctx):
        result = ctx("How to control the mind?")
        assert len(result["graph_context"]) > 0


class TestNoFalsePositives:
    """Verify that generic words don't produce spurious matches."""

    def test_hello_matches_nothing(self, ctx):
        result = ctx("Hello, how are you?")
        assert result["matched_concepts"] == []

    def test_weather_matches_nothing(self, ctx):
        result = ctx("What is the weather today?")
        assert result["matched_concepts"] == []

    def test_nature_does_not_match_prakriti(self, ctx):
        """'nature' alone should not match Prakriti (known false positive fix)."""
        result = ctx("What is the nature of the soul?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Prakriti" not in names
        # Should match Atman via 'soul'
        assert "Atman" in names


class TestHindiQueries:
    """Verify that Hindi/Sanskrit keywords also match."""

    def test_hindi_atma(self, ctx):
        result = ctx("आत्मा क्या है?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Atman" in names

    def test_hindi_shanti(self, ctx):
        result = ctx("शांति कैसे मिलेगी?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Shanti" in names

    def test_hindi_krodha(self, ctx):
        result = ctx("क्रोध पर नियंत्रण कैसे करें?")
        names = {c["name"] for c in result["matched_concepts"]}
        assert "Krodha" in names
