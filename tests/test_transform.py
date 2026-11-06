from __future__ import annotations

from accent_theme.accent import Accent, rgb_to_hsv
from accent_theme.transform import boost_saturation


def test_boost_saturation_keeps_neutral_colors() -> None:
    assert boost_saturation({"surface": "#080808"}, 1.45) == {"surface": "#080808"}


def test_boost_saturation_clamps_at_full_chroma() -> None:
    assert boost_saturation({"primary": "#ff0000"}, 1.45) == {"primary": "#ff0000"}


def test_boost_saturation_leaves_non_hex_values() -> None:
    assert boost_saturation({"surface": "transparent"}, 1.45) == {
        "surface": "transparent"
    }


def test_boost_saturation_increases_chroma() -> None:
    original = Accent(0x84, 0xCF, 0xFF)
    boosted = boost_saturation({"primary": "#84cfff"}, 1.45)["primary"]
    result = Accent(
        int(boosted[1:3], 16),
        int(boosted[3:5], 16),
        int(boosted[5:7], 16),
    )

    assert rgb_to_hsv(result).saturation > rgb_to_hsv(original).saturation
    assert rgb_to_hsv(result).saturation <= 1.0
