import argparse
# from rntchangesfunctions import to_bool
# from rntchangesfunctions import multi_value


def parse_recent_args(parser):
    parser.add_argument("argone", help="First required argument keyword search or the search time in seconds")
    parser.add_argument("argtwo", help="Second required argument the search time for recentchanges search or noarguser")
    parser.add_argument("USR", help="Username")
    parser.add_argument("PWD", help="Password")
    parser.add_argument("argf", nargs="?", default="bnk", help="Optional argf or inverted (default: bnk)")
    parser.add_argument("method", nargs="?", default="", help="Optional method rnt means recentchanges \"\" means recentchanges search (default: empty)")

    return parser


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run recentchanges from cmdline 4 required 9 optional"
    )
    parser = parse_recent_args(parser)

    return parser
