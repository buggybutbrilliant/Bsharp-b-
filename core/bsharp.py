#!/usr/bin/env python3
# B# (B-sharp) Programming Language  v1.2.0
# Entry point — all logic lives in separate modules
def main_entry():
    from cmd.cli import main
    main()

if __name__ == '__main__':
    main_entry()