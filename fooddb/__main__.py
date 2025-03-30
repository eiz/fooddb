import sys

from fooddb.cli import cli

if __name__ == "__main__":
    # If no arguments, default to run-server
    if len(sys.argv) == 1:
        # Add the run-server command to the arguments
        sys.argv.append("run-server")
    
    cli()