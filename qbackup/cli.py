"""
CLI interface functions
"""

import argparse


def manage_vm(args) -> None:
    print(f"Manage vm {args.action}")


def manage_group(args) -> None:
    print(f"Manage group {args.action}")


def main():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    vm_parser = subparsers.add_parser("vm")
    vm_parser.add_argument("action", choices=["add", "del", "list"])
    vm_parser.set_defaults(function=manage_vm)

    group_parser = subparsers.add_parser("group")
    group_parser.add_argument("action", choices=["add", "del", "list"])
    group_parser.set_defaults(function=manage_group)

    args = parser.parse_args()
    args.function(args)
