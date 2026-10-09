"""Snippet parsing. Every snippet string below is copied verbatim from a recorded S-01 fixture."""

import pytest

from app.pipeline.cleaning import (
    detect_portal,
    find_prices,
    is_rental_page,
    normalize_text,
    parse_area_sqft,
    parse_bedrooms,
    parse_price_inr,
    parse_price_per_sqft,
    parse_property_type,
    parse_status,
    snippet_entries,
)
from app.schemas.listing import Portal, SaleStatus
from app.schemas.profile import PropertyType, Segment


@pytest.mark.parametrize(
    "text,inr",
    [
        ("SOWPARNIKA COLUMNS · ₹60 Lac. ₹8,185 /sqft", 6_000_000),
        ("4 BHK Flat For Sale In Whitefield. ₹1.70 Cr. ₹7,234/sq.ft.", 17_000_000),
        ("3 BHK Apartment In K Squre Regium For Sale In Hebbal · 96.48 Lacs.", 9_648_000),
        ("Priced at rs4.65 crore,", 46_500_000),
        ("₹75 Lacs ₹6 ...", 7_500_000),
    ],
)
def test_prices(text, inr):
    assert parse_price_inr(text) == inr


@pytest.mark.parametrize(
    "text",
    [
        "available for sale at an average price of ₹4.59 Cr and a median price of ₹2.62 Cr",
        "with 1 to 6 BHK options available, priced between ₹68.55 lakh and",
        "within a budget of 80 lakhs.",
        "Buy Ready to move, Resale, apartments/flats in Hebbal within ₹ 1 Crore.",
        "EMI: ₹2.25 Lacs/m",
        "Find Flats in Whitefield, Bangalore from 50 lakhs to 80 lakhs on 99acres.com.",
    ],
)
def test_filters_statistics_and_instalments_are_not_prices(text):
    assert parse_price_inr(text) is None


def test_ranges_and_starting_prices_keep_the_lower_bound_with_a_note():
    (low,) = find_prices("Bangalore ₹97.8 Lac - 2.9 cr ₹7,662 /sqft")
    assert low.inr == 9_780_000 and "range" in low.note
    (low,) = find_prices("₹1.25 - 1.28 Cr ₹10,241 /sqft Under Construction")
    assert low.inr == 12_500_000
    first, second = find_prices("3, 4 BHK Apartment · ₹3.57 Cr+. 4BHK₹4.82 Cr+")
    assert (first.inr, first.note, second.inr) == (35_700_000, "starting price", 48_200_000)


def test_math_bold_text_is_normalised():
    title = "Flats in Hebbal Bangalore for Sale under ₹ 𝟏 𝐂𝐫𝐨𝐫𝐞"  # noqa: RUF001  (verbatim MagicBricks)
    assert normalize_text(title).endswith("₹ 1 Crore")


def test_price_per_sqft_and_area():
    assert parse_price_per_sqft("₹60 Lac. ₹8,185 /sqft") == 8185
    assert parse_price_per_sqft("₹55 Lacs. ₹4,400/sq.ft.") == 4400
    assert parse_price_per_sqft("for Resale in ₹29 Cr ₹16111 / sqft.") == 16111
    assert parse_area_sqft("Ready To Move 735 sqft(68 sqm) bedrooms") == 735
    assert parse_area_sqft("ranging from 1415.0 sq. ft. to 1470.0 sq. ft.,") == 1415
    assert parse_area_sqft("offers 950 sq.Ft. featuring 2 bedrooms") == 950
    assert parse_area_sqft("68 sqm") == pytest.approx(731.9, abs=0.1)  # x 10.7639
    assert parse_area_sqft("Find Shops for sale in Bangalore from 2000 sq ft to 2500 sq ft") is None


def test_bedrooms_status_and_type():
    assert parse_bedrooms("4+ BHK House For Sale In R T Nagar") == 4
    assert parse_bedrooms("3, 4 BHK Apartment · ₹3.57 Cr+") is None  # several sizes
    assert parse_status("Resale ₹76 Lac ₹10,340 /sqft Ready To Move") is SaleStatus.READY_TO_MOVE
    assert parse_status("Resale ₹2 Cr ₹40,000 /sqft.") is SaleStatus.RESALE
    residential = Segment.RESIDENTIAL
    assert parse_property_type("Builder floor apartment is available", residential) is (
        PropertyType.BUILDER_FLOOR
    )
    assert parse_property_type("Shop in Indiranagara , Bangalore", Segment.COMMERCIAL) is (
        PropertyType.SHOP_SHOWROOM
    )
    assert parse_property_type("Shop in Indiranagara , Bangalore", residential) is None


def test_portals_and_rental_pages():
    assert detect_portal("https://www.99acres.com/x-ffid") is Portal.NINETY_NINE_ACRES
    assert detect_portal("https://www.olx.in/whitefield") is None
    assert is_rental_page("Warehouse/Godown For Rent in KR Puram, Bangalore", "https://x")
    assert is_rental_page("Commercial", "https://www.magicbricks.com/a-pppfr")
    assert not is_rental_page("Flats for Sale in Whitefield", "https://www.magicbricks.com/a-pppfs")


def test_named_99acres_entries():
    snippet = (
        "Ready to move Flats / Apartments in Whitefield, Bangalore for Sale Below 80 Lakhs ; "
        "SOWPARNIKA COLUMNS · ₹60 Lac. ₹8,185 /sqft ; GODREJ SPLENDOUR · ₹69.3 Lac. ₹ ..."
    )
    first, second = snippet_entries(snippet)
    assert (first.project_name, first.price_inr, first.price_per_sqft) == (
        "Sowparnika Columns",
        6_000_000,
        8185,
    )
    assert first.size_sqft == pytest.approx(733.0) and first.size_computed  # 60 L / 8,185
    assert (second.project_name, second.price_inr) == ("Godrej Splendour", 6_930_000)


def test_nobroker_entries_priced_by_rate_and_size():
    snippet = (
        "2 BHK Apartment In Rs Abode Apartments For Sale In Hebbal · ₹7,600/sq.ft · 1250 sqft ; "
        "3 BHK House For Sale In Hebbal · ₹6,857/sq.ft · 1400 sqft ; 4+ BHK House For ..."
    )
    first, second = snippet_entries(snippet)
    assert first.project_name == "Rs Abode Apartments"
    assert (first.price_inr, first.price_computed, first.bedrooms) == (9_500_000, True, 2)
    assert second.headline == "3 BHK House For Sale In Hebbal"


def test_two_entries_in_one_segment():
    snippet = (
        "Flat in Whitefield, Bangalore Resale ₹77 Lac ₹12,520 /sqft Ready To Move 615 sqft(57 "
        "sqm) 1 bedroom(s), 1 bathroom and 1 balcony. ₹90 Lac ₹6,896 /sqft Ready ... ..."
    )
    first, second = snippet_entries(snippet)
    assert (first.price_inr, first.size_sqft, first.status) == (
        7_700_000,
        615,
        SaleStatus.READY_TO_MOVE,
    )
    assert (second.price_inr, second.price_per_sqft) == (9_000_000, 6896)


def test_magicbricks_price_first_entry():
    snippet = (
        "₹1.45 Cr 2 BHK. 2 BHK Builder Floor for Sale in Jayanagar Bangalore. Super Area. "
        "1100 sqft. Status. Ready to Move. Builder floor apartment is available for ..."
    )
    (entry,) = snippet_entries(snippet)
    assert entry.price_inr == 14_500_000 and entry.size_sqft == 1100 and entry.bedrooms == 2
    assert entry.headline == "2 BHK Builder Floor for Sale in Jayanagar Bangalore"


def test_statistics_only_snippet_has_no_entries():
    snippet = (
        "The residential land/plots in Yelahanka are available for sale at an average price of "
        "₹4.59 Cr and a median price of ₹2.62 Cr, with a QoQ growth of -3.93%."
    )
    assert snippet_entries(snippet) == []


def test_search_page_blurbs_are_not_names():
    snippet = (
        "Find over 28+ 2 BHK Flats for sale in Whitefield-Hoskote Road Bangalore under 90 Lakhs. "
        "₹84 Lac 2 BHK … 950 sqft Status Ready to Move"
    )
    (entry,) = snippet_entries(snippet)
    assert entry.price_inr == 8_400_000 and entry.headline is None


def test_price_per_sqft_only_attaches_to_its_own_price():
    snippet = (
        "The under construction building/office will be available within 3 months. "
        "The property is available at 1.91 crore. sale ₹40,000 ₹66 /sqft"
    )
    (entry,) = snippet_entries(snippet)
    assert entry.price_inr == 19_100_000
    assert entry.price_per_sqft is None and entry.size_sqft is None


def test_filter_phrases_are_not_headlines():
    snippet = (
        "Office Space for sale in Bangalore from 1 crore to 1.5 crores , Bangalore Resale ₹1.3 Cr "
        "₹15,853 /sqft Under Construction Under Construction 623 sqft(58 sqm) ..."
    )
    (entry,) = snippet_entries(snippet)
    assert entry.headline is None and entry.price_inr == 13_000_000 and entry.size_sqft == 623


def test_bedroom_counts_written_out():
    assert parse_bedrooms("comprises 2 bedrooms, 3 bathrooms .") == 2
    assert parse_bedrooms("615 sqft(57 sqm) 1 bedroom(s), 1 bathroom") == 1
    assert parse_bedrooms("2 and 3 bedroom apartment.") is None


def test_stated_size_range_precedes_price_divided_by_rate():
    (entry,) = snippet_entries(
        "ranging from 1415.0 sq. ft. to 1470.0 sq. ft., ₹1.25 - 1.28 Cr ₹10,241 /sqft"
    )
    assert entry.size_sqft == 1415 and not entry.size_computed


def test_page_filter_status_is_not_a_property_status():
    (entry,) = snippet_entries(
        "Choose from over 22+ Flats. Buy Ready to move, Resale, apartments/flats in Hebbal "
        "within ₹ 1 Crore. ₹1.15 Cr"
    )
    assert entry.status is None
    assert parse_status("Buy Ready to move, Resale, apartments. Status. Under Construction") == (
        SaleStatus.UNDER_CONSTRUCTION
    )


def test_page_description_price_is_not_an_entry():
    assert (
        snippet_entries(
            "Finding for resale or new flats for sale below 60 lakhs in Electronic City … "
            "45 Lakhs Flats for"
        )
        == []
    )
    (entry,) = snippet_entries("₹45 Lakhs. 2 BHK Flat for sale in Electronic City. 950 sqft")
    assert entry.price_inr == 4_500_000
