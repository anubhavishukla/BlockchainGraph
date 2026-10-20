
from pathlib import Path
import argparse
import json

import networkx as nx
import pandas as pd


def split_values(value):
    """Convert pipe-separated wallet addresses into a list."""
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


def build_graph(csv_path=None):
    """Build and return a directed transaction graph."""
    if csv_path is None:
        csv_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "transactions.csv"
        )

    df = pd.read_csv(csv_path)

    required = {"input_addresses", "output_addresses", "txid"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required CSV columns: {sorted(missing)}"
        )

    graph = nx.MultiDiGraph()

    for _, row in df.iterrows():
        inputs = split_values(row["input_addresses"])
        outputs = split_values(row["output_addresses"])

        for wallet in inputs + outputs:
            graph.add_node(wallet)

        for source in inputs:
            for destination in outputs:
                graph.add_edge(
                    source,
                    destination,
                    txid=str(row["txid"]),
                )

    return graph


def analyze_connected_wallets(wallet, graph=None):
    """Return connected-wallet analysis as reusable Python data."""
    if not isinstance(wallet, str) or not wallet.strip():
        return {
            "success": False,
            "error": "Wallet ID must be a non-empty string.",
        }

    wallet = wallet.strip()

    try:
        if graph is None:
            graph = build_graph()
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        return {
            "success": False,
            "error": f"Could not load transaction graph: {exc}",
        }

    if wallet not in graph:
        return {
            "success": False,
            "wallet": wallet,
            "error": f"Wallet '{wallet}' was not found in the graph.",
        }

    incoming = sorted(set(graph.predecessors(wallet)))
    outgoing = sorted(set(graph.successors(wallet)))

    return {
        "success": True,
        "wallet": wallet,
        "incoming": incoming,
        "outgoing": outgoing,
        "connected": sorted(set(incoming + outgoing)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze connected wallets in the transaction graph."
    )
    parser.add_argument(
        "wallet",
        nargs="?",
        help="Wallet ID to analyze, for example W500",
    )
    args = parser.parse_args()

    graph = build_graph()

    if args.wallet is None:
        print(json.dumps({
            "success": True,
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "message": "Pass a wallet ID to analyze its connections.",
        }, indent=2))
    else:
        result = analyze_connected_wallets(args.wallet, graph)
        print(json.dumps(result, indent=2))

        if not result["success"]:
            raise SystemExit(1)
