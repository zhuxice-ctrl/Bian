from trading_learning.cli import build_parser


def test_cli_has_expected_commands():
    parser = build_parser()
    command_names = {
        action.dest
        for action in parser._subparsers._group_actions[0]._choices_actions
    }
    assert {"init-db", "backtest-ma", "export"}.issubset(command_names)
