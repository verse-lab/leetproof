from utils.spec_bug_finder import _implementation_name, _implementation_parameter_binders


def test_finds_concrete_implementation_and_skips_sorry_stub():
    assert _implementation_name("section Impl\ndef rolling_max (xs : List Int) := xs\nend Impl") == "rolling_max"
    assert _implementation_name("section Impl\ndef implementation (xs : List Int) := sorry\nend Impl") is None


def test_recovers_parameter_names_from_generated_test_bindings():
    binders, args = _implementation_parameter_binders(
        "test12",
        [
            ("test12_numbers", "List Int", "[-3]"),
            ("test12_Expected", "List Int", "[0]"),
        ],
    )
    assert binders == "(numbers : List Int)"
    assert args == "numbers"
