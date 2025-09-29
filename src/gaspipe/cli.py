import argparse
from . import project_manager

def main():
    parser = argparse.ArgumentParser(prog="gaspipe")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("resume")
    sub.add_parser("validate-config")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.cmd == "run":
        project_manager.run()
    elif args.cmd == "resume":
        project_manager.resume()
    elif args.cmd == "validate-config":
        project_manager.validate_config()
    elif args.cmd == "self-test":
        project_manager.self_test()

if __name__ == "__main__":
    main()
