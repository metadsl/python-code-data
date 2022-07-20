import pytest

from code_data._line_mapping import (
    CollapsedLineTableItem,
    LineMapping,
    LineTableItem,
    collapse_items,
    expand_items,
    items_to_mapping,
    mapping_to_items,
)

COLLAPSE_PARAMS = [
    pytest.param(
        # from turtledemo.minimal_hanoi
        [
            LineTableItem(line_offset=2, bytecode_offset=0),
            LineTableItem(line_offset=0, bytecode_offset=6),
            LineTableItem(line_offset=0, bytecode_offset=6),
        ],
        [
            CollapsedLineTableItem(line_offset=2, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=6),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=6),
        ],
        False,
        id="dont collapse small",
    ),
    pytest.param(
        # from long jump
        [
            LineTableItem(line_offset=0, bytecode_offset=255),
            LineTableItem(line_offset=1, bytecode_offset=153),
            LineTableItem(line_offset=1, bytecode_offset=8),
        ],
        [
            CollapsedLineTableItem(line_offset=1, bytecode_offset=408),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=8),
        ],
        False,
        id="collapse big bytecode offset",
    ),
    pytest.param(
        # from idlelib.idle_test.test_hyperparser
        [
            LineTableItem(line_offset=127, bytecode_offset=18),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=0, bytecode_offset=0),
            LineTableItem(line_offset=1, bytecode_offset=8),
        ],
        [
            CollapsedLineTableItem(line_offset=127 + 127, bytecode_offset=18),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=8),
        ],
        False,
        id="Exactly 127 * 2 line offset",
    ),
    pytest.param(
        # From astroid.brain.brain_numpy_ndarray
        [
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=1, bytecode_offset=4),
            LineTableItem(line_offset=1, bytecode_offset=6),
            LineTableItem(line_offset=4, bytecode_offset=2),
        ],
        [
            CollapsedLineTableItem(line_offset=127, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=6),
            CollapsedLineTableItem(line_offset=4, bytecode_offset=2),
        ],
        False,
        id="line offset prev 0 dont expand",
    ),
    pytest.param(
        [
            LineTableItem(line_offset=127, bytecode_offset=4),
            LineTableItem(line_offset=1, bytecode_offset=0),
        ],
        [CollapsedLineTableItem(line_offset=128, bytecode_offset=4)],
        False,
        id="long line jump 3.7",
    ),
    pytest.param(
        [
            LineTableItem(line_offset=0, bytecode_offset=4),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=1, bytecode_offset=8),
        ],
        [
            CollapsedLineTableItem(line_offset=0, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=128, bytecode_offset=8),
        ],
        True,
        id="long line jump 3.10",
    ),
    pytest.param(
        [
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=127, bytecode_offset=0),
            LineTableItem(line_offset=26, bytecode_offset=254),
            LineTableItem(line_offset=0, bytecode_offset=234),
        ],
        [CollapsedLineTableItem(line_offset=1042, bytecode_offset=488)],
        True,
        id="long line and bytecode jump 3.10",
    ),
]


@pytest.mark.parametrize(
    "test",
    [pytest.param("collapse", id="collapse"), pytest.param("expand", id="expand")],
)
@pytest.mark.parametrize("expanded,collapsed,is_linetable", COLLAPSE_PARAMS)
def test_collapse_expand(expanded, collapsed, is_linetable, test):
    if test == "collapse":
        assert collapse_items(expanded, is_linetable) == collapsed
    elif test == "expand":
        assert expand_items(collapsed, is_linetable) == expanded


MAPPING_PARAMS = [
    pytest.param(
        # From sphinx_comments on Python 3.8
        [
            CollapsedLineTableItem(line_offset=1, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=-1, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=2, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=-2, bytecode_offset=2),
        ],
        LineMapping(
            offset_to_line={0: 1, 2: 1, 4: 3, 6: 1, 8: 1, 10: 1, 12: 1},
            offset_to_additional_line_offsets={2: [-1]},
        ),
        14,
        False,
    ),
    pytest.param(
        # pre_commit.languages.r on Python 3.9
        [
            CollapsedLineTableItem(line_offset=5, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=10),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=10),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=14),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=18),
            CollapsedLineTableItem(line_offset=2, bytecode_offset=28),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=28, bytecode_offset=12),
            CollapsedLineTableItem(line_offset=-30, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=32, bytecode_offset=6),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=12),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=-1, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=-2, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=3, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=-3, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=4, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=-4, bytecode_offset=2),
        ],
        LineMapping(
            offset_to_line={
                0: 5,
                2: 5,
                4: 5,
                6: 5,
                8: 5,
                10: 6,
                12: 6,
                14: 6,
                16: 6,
                18: 6,
                20: 7,
                22: 7,
                24: 7,
                26: 7,
                28: 7,
                30: 7,
                32: 7,
                34: 8,
                36: 8,
                38: 8,
                40: 8,
                42: 8,
                44: 8,
                46: 8,
                48: 8,
                50: 8,
                52: 9,
                54: 9,
                56: 9,
                58: 9,
                60: 9,
                62: 9,
                64: 9,
                66: 9,
                68: 9,
                70: 9,
                72: 9,
                74: 9,
                76: 9,
                78: 9,
                80: 11,
                82: 12,
                84: 12,
                86: 12,
                88: 12,
                90: 13,
                92: 13,
                94: 13,
                96: 13,
                98: 13,
                100: 13,
                102: 41,
                104: 11,
                106: 11,
                108: 11,
                110: 43,
                112: 43,
                114: 44,
                116: 44,
                118: 44,
                120: 44,
                122: 44,
                124: 44,
                126: 45,
                128: 46,
                130: 46,
                132: 45,
                134: 46,
                136: 45,
                138: 48,
                140: 45,
                142: 45,
                144: 49,
                146: 45,
                148: 45,
                150: 45,
                152: 45,
                154: 45,
                156: 45,
                158: 45,
                160: 45,
                162: 45,
                164: 45,
                166: 45,
                168: 45,
                170: 45,
                172: 45,
                174: 45,
            },
            offset_to_additional_line_offsets={86: [0], 88: [0], 136: [0, 1, -2]},
        ),
        176,
        False,
        id="zero line offset followed by zero bytecode offset",
    ),
    # From setuptools.config
    pytest.param(
        [
            CollapsedLineTableItem(line_offset=2, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=2),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=10),
            CollapsedLineTableItem(line_offset=0, bytecode_offset=0),
            CollapsedLineTableItem(line_offset=-2, bytecode_offset=12),
        ],
        LineMapping(
            offset_to_line={
                0: 0,
                2: 0,
                4: 2,
                6: 3,
                8: 3,
                10: 3,
                12: 3,
                14: 3,
                16: 3,
                18: 3,
                20: 3,
                22: 3,
                24: 3,
                26: 3,
                28: 1,
                30: 1,
                32: 1,
                34: 1,
                36: 1,
                38: 1,
                40: 1,
                42: 1,
                44: 1,
            },
            offset_to_additional_line_offsets={16: [0, 0]},
        ),
        46,
        False,
        id="multiple zero line offsets",
    ),
    pytest.param(
        # x + y
        # z
        [
            CollapsedLineTableItem(line_offset=0, bytecode_offset=8),
            CollapsedLineTableItem(line_offset=1, bytecode_offset=8),
        ],
        LineMapping(
            offset_to_line={
                0: 0,
                2: 0,
                4: 0,
                6: 0,
                8: 1,
                10: 1,
                12: 1,
                14: 1,
            },
            offset_to_additional_line_offsets={},
        ),
        18,
        True,
        id="two lines, linetable",
    ),
    pytest.param(
        [CollapsedLineTableItem(line_offset=128, bytecode_offset=4)],
        LineMapping(
            offset_to_line={0: 0, 2: 0, 4: 128, 6: 128, 8: 128, 10: 128},
            offset_to_additional_line_offsets={},
        ),
        12,
        False,
        id="long line jump 3.7",
    ),
    pytest.param(
        [
            CollapsedLineTableItem(line_offset=0, bytecode_offset=4),
            CollapsedLineTableItem(line_offset=128, bytecode_offset=8),
        ],
        LineMapping(
            offset_to_line={0: 0, 2: 0, 4: 128, 6: 128, 8: 128, 10: 128},
            offset_to_additional_line_offsets={},
        ),
        12,
        True,
        id="long line jump 3.10",
    ),
]


@pytest.mark.parametrize(
    "test",
    [
        pytest.param("to_mapping", id="to_mapping"),
        pytest.param("from_mapping", id="from_mapping"),
    ],
)
@pytest.mark.parametrize("collapsed,mapping,max_offset,is_linetable", MAPPING_PARAMS)
def test_to_from_mapping(collapsed, mapping, max_offset, is_linetable, test):
    if test == "to_mapping":
        assert items_to_mapping(collapsed, max_offset, is_linetable) == mapping
    elif test == "from_mapping":
        assert mapping_to_items(mapping, is_linetable) == collapsed
