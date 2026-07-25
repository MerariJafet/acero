"""CCC-8: novelty taxonomy + ContributionScore (offline)."""

from __future__ import annotations

from acero.science.contribution import (
    ContributionComponents,
    NoveltyType,
    SourceFamily,
    assess,
    bibliographic_novelty,
    contribution_band,
    contribution_score,
    weighted_novelty,
)


def test_not_found_novelty_confidence_scales_with_coverage():
    thin = bibliographic_novelty(False, {SourceFamily.PEER_REVIEWED})
    wide = bibliographic_novelty(False, set(SourceFamily))
    assert thin.novelty == 1.0 and wide.novelty == 1.0
    assert thin.confidence < wide.confidence          # looked less → less sure
    assert "no es 'nuevo'" in thin.caveat


def test_found_equivalent_zeroes_novelty():
    b = bibliographic_novelty(True, {SourceFamily.PEER_REVIEWED})
    assert b.novelty == 0.0


def test_scientific_novelty_dominates_weighting():
    only_biblio = weighted_novelty({NoveltyType.BIBLIOGRAPHIC: 1.0})
    only_scientific = weighted_novelty({NoveltyType.SCIENTIFIC: 1.0})
    # per-type max is 1.0 for each in isolation; test the MIX instead
    mixed_biblio = weighted_novelty({NoveltyType.BIBLIOGRAPHIC: 1.0,
                                     NoveltyType.SCIENTIFIC: 0.0})
    mixed_sci = weighted_novelty({NoveltyType.BIBLIOGRAPHIC: 0.0,
                                  NoveltyType.SCIENTIFIC: 1.0})
    assert mixed_sci > mixed_biblio
    assert only_biblio == only_scientific == 1.0     # each alone normalizes to itself


def test_trivial_but_novel_result_collapses_to_low_contribution():
    # high novelty, near-zero scientific importance → product collapses
    c = ContributionComponents(novelty=1.0, evidential_strength=0.8,
                               scientific_importance=0.02, robustness=0.9,
                               mechanistic_value=0.5)
    assert contribution_score(c) < 0.05
    assert contribution_band(contribution_score(c)) == "trivial"


def test_strong_all_round_result_scores_major():
    c = ContributionComponents(0.9, 0.9, 0.9, 0.9, 0.9)
    s = contribution_score(c)
    assert s >= 0.5 and contribution_band(s) == "mayor"


def test_assess_report_shape():
    rep = assess(ContributionComponents(0.5, 0.5, 0.5, 0.5, 0.5),
                 bibliographic_novelty(False, {SourceFamily.PEER_REVIEWED}))
    s = rep.summary()
    assert "score" in s and "band" in s and s["bibliographic_caveat"]
