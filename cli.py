import sys
from src.agent import run_agent

def main():
    print("Sanctions Knowledge Graph — Agent CLI")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            query = input("Query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not query:
            continue

        if query.lower() in ("quit", "exit"):
            print("Exiting.")
            break

        run_agent(query, verbose=True)


if __name__ == "__main__":
    main()