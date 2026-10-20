
from pathlib import Path
import argparse
import json

import networkx as nx
import pandas as pd


def split_values(value):
    if pd.isna(value):
        return []
    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


def build_graph(csv_path=None):
    """Build and return the wallet transaction graph."""
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


def analyze_wallets(graph=None, csv_path=None):
    """Return wallet degree statistics as reusable data."""
    if graph is None:
        graph = build_graph(csv_path)

    wallets = []
    for wallet in sorted(graph.nodes()):
        wallets.append({
            "wallet": wallet,
            "incoming": graph.in_degree(wallet),
            "outgoing": graph.out_degree(wallet),
            "total_degree": graph.degree(wallet),
        })

    return {
        "success": True,
        "total_wallets": graph.number_of_nodes(),
        "wallets": wallets,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze wallet transaction statistics."
    )
    parser.add_argument(
        "--wallet",
        help="Optionally analyze one wallet, for example W058",
    )
    args = parser.parse_args()

    graph = build_graph()
    result = analyze_wallets(graph)

    if args.wallet:
        matching = [
            item for item in result["wallets"]
            if item["wallet"] == args.wallet.strip()
        ]
        if not matching:
            print(json.dumps({
                "success": False,
                "error": f"Wallet '{args.wallet}' was not found.",
            }, indent=2))
            raise SystemExit(1)

        print(json.dumps(matching[0], indent=2))
    else:
        print(json.dumps({
            "success": True,
            "total_wallets": result["total_wallets"],
            "sample_wallets": result["wallets"][:10],
            "message": "Use the Python function to access all wallet results.",
        }, indent=2))
