import pytest

from app.schemas.provenance import ExtractionMethod
from app.services.alerts import diff_matches, price_identity
from tests.unit.test_verification import candidate


def listing(key="old", price=6_000_000):
    item = candidate()
    item.id = key
    item.name = "Sample Gardens"
    item.evidence = "SAMPLE GARDENS · ₹60 Lac. 1200 sqft"
    item.price_inr.value = price
    item.size_sqft.value = 1200
    item.size_sqft.method = ExtractionMethod.REGEX
    return item


def test_changed_price_id_links_only_unambiguous_explicit_project_and_stated_size():
    old, new = listing(), listing("new", 5_000_000)
    [(kind, item, message)] = diff_matches([old], [new], {old.id})
    assert kind == "price_drop" and item == new and "6,000,000" in message
    assert "confirm the same unit" in message


@pytest.mark.parametrize("price", [6_000_000, 7_000_000, None])
def test_same_project_with_equal_higher_or_unknown_price_is_not_a_drop(price):
    assert diff_matches([listing()], [listing("new", price)], {"old"}) == []


def test_ambiguous_project_quotes_do_not_claim_price_drop():
    events = diff_matches([listing(), listing("other")], [listing("new", 5_000_000)], {"old"})
    assert {event[0] for event in events} == {"new_match"}


def test_generic_names_and_computed_sizes_do_not_link_different_ids():
    item = listing()
    item.evidence = "2 BHK Flat for sale in Whitefield. ₹60 Lac. 1200 sqft"
    assert price_identity(item) is None
    item = listing()
    item.size_sqft.method = ExtractionMethod.COMPUTED
    assert price_identity(item) is None


def test_previously_seen_match_is_not_new_and_same_id_can_drop():
    assert diff_matches([], [listing()], {"old"}) == []
    assert diff_matches([listing()], [listing(price=5_000_000)], {"old"})[0][0] == "price_drop"
