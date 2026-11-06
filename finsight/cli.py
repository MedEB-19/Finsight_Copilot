"""One CLI for every pipeline step:  python -m finsight.cli <command>"""
import argparse
import logging


def main():
    p = argparse.ArgumentParser(prog="finsight")
    p.add_argument("command", choices=["init-db", "companies", "prices", "fundamentals", "ratios",
                                       "filings", "index", "all", "refresh", "ask"])
    p.add_argument("--tickers", nargs="*", help="limit to some tickers (default: all 44)")
    p.add_argument("--question", help="for the 'ask' command")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tk = [t.upper() for t in a.tickers] if a.tickers else None

    steps = {
        "init-db": lambda: __import__("finsight.db.init_db", fromlist=["x"]).init_db(),
        "companies": lambda: __import__("finsight.ingestion.companies", fromlist=["x"]).load_companies(),
        "prices": lambda: __import__("finsight.ingestion.prices", fromlist=["x"]).load_prices(tk),
        "fundamentals": lambda: __import__("finsight.ingestion.fundamentals", fromlist=["x"]).load_fundamentals(tk),
        "ratios": lambda: __import__("finsight.ingestion.ratios", fromlist=["x"]).load_ratios(),
        "filings": lambda: __import__("finsight.ingestion.edgar", fromlist=["x"]).download_filings(tk),
        "index": lambda: __import__("finsight.ingestion.embed", fromlist=["x"]).build_index(tk),
    }
    if a.command == "all":
        for s in ["init-db", "companies", "prices", "fundamentals", "ratios", "filings", "index"]:
            logging.info("=== %s ===", s)
            steps[s]()
    elif a.command == "refresh":  # what the daily scheduled task runs
        for s in ["prices", "ratios"]:
            steps[s]()
    elif a.command == "ask":
        from finsight.agent.graph import ask
        r = ask(a.question or "Give me an overview of AAPL")
        print(r["answer"], "\n\nTools:", r["tools_used"])
    else:
        steps[a.command]()


if __name__ == "__main__":
    main()
