
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
    """Build a wallet -> transaction -> wallet directed graph."""
    if csv_path is None:
        csv_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "transactions.csv"
        )

    df = pd.read_csv(csv_path)

    required = {
        "txid",
        "input_addresses",
        "output_addresses",
        "timestamp",
    }
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required CSV columns: {sorted(missing)}"
        )

    graph = nx.DiGraph()

    for _, row in df.iterrows():
        txid = str(row["txid"]).strip()
        if not txid or txid.lower() == "nan":
            continue

        transaction_node = f"TX_{txid}"
        inputs = split_values(row["input_addresses"])
        outputs = split_values(row["output_addresses"])

        graph.add_node(
            transaction_node,
            node_type="transaction",
            timestamp=str(row["timestamp"]),
        )

        for wallet in inputs:
            graph.add_node(wallet, node_type="wallet")
            graph.add_edge(
                wallet,
                transaction_node,
                relationship="input",
            )

        for wallet in outputs:
            graph.add_node(wallet, node_type="wallet")
            graph.add_edge(
                transaction_node,
                wallet,
                relationship="output",
            )

    return graph


def graph_summary(graph=None, csv_path=None):
    """Return graph statistics as a reusable dictionary."""
    if graph is None:
        graph = build_graph(csv_path)

    wallet_nodes = [
        node for node, data in graph.nodes(data=True)
        if data.get("node_type") == "wallet"
    ]

    transaction_nodes = [
        node for node, data in graph.nodes(data=True)
        if data.get("node_type") == "transaction"
    ]

    return {
        "success": True,
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "wallet_nodes": len(wallet_nodes),
        "transaction_nodes": len(transaction_nodes),
        "sample_edges": [
            {
                "source": source,
                "destination": destination,
                "relationship": data.get("relationship"),
            }
            for source, destination, data
            in list(graph.edges(data=True))[:15]
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build and summarize the transaction graph."
    )
    parser.add_argument(
        "--csv",
        help="Optional path to a transaction CSV file",
    )
    args = parser.parse_args()

    result = graph_summary(csv_path=args.csv)
    print(json.dumps(result, indent=2))
