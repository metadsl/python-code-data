

from pytest import param, mark
from code_data.line_table import LineMapping, LineTableItem, collapse_items, expand_items, items_to_mapping, mapping_to_items


EXAMPLES = [
    param(
        [LineTableItem(line_offset=0, bytecode_offset=8)],
        [LineTableItem(line_offset=0, bytecode_offset=8)],
        LineMapping({0: 1, 2: 1, 4: 1, 6: 1, 8: 1, 10: 1}, {8: [0]}),
        12,
        id="class with empty body"
    )
]

@mark.parametrize("expanded_items,collapsed_items,mapping,max_offset", EXAMPLES)
def test_to_mapping(expanded_items, collapsed_items, mapping, max_offset):
    assert collapse_items(expanded_items) == collapsed_items, "collapse_items"
    assert expand_items(expanded_items) == expanded_items, "expand_items"
    assert items_to_mapping(collapsed_items, max_offset) == mapping, "items_to_mapping"
    assert mapping_to_items(mapping) == collapsed_items, "mapping_to_items"
    

