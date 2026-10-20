from pathlib import Path

import pandas as pd
import networkx as nx


TIMESTAMP_COLUMNS = [
    "timestamp",
    "transaction_timestamp",
    "block_timestamp",
    "time",
    "datetime",
    "date",
]


def split_values(value):
    """Convert pipe-separated wallet addresses into a list."""
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


def build_graph(df):
    """Build a directed multigraph from a transactions DataFrame."""
    required = {"input_addresses", "output_addresses", "txid"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    timestamp_col = next(
        (col for col in TIMESTAMP_COLUMNS if col in df.columns),
        None,
    )

    if timestamp_col is None:
        raise ValueError(
            "No transaction timestamp column found. "
            f"Available columns: {list(df.columns)}"
        )

    graph = nx.MultiDiGraph()

    for _, row in df.iterrows():
        timestamp = pd.to_datetime(
            row[timestamp_col], errors="coerce", utc=True
        )

        inputs = split_values(row["input_addresses"])
        outputs = split_values(row["output_addresses"])

        for wallet in inputs + outputs:
            graph.add_node(wallet)

        if pd.isna(timestamp):
            continue

        for source in inputs:
            for destination in outputs:
                graph.add_edge(
                    source,
                    destination,
                    txid=str(row["txid"]),
                    timestamp=timestamp,
                )

    return graph


def load_graph(csv_path=None):
    """Load transactions and return a graph."""
    if csv_path is None:
        csv_path = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"

    df = pd.read_csv(csv_path)
    return build_graph(df)


def trace_transaction_path(source, destination, graph=None, start_time=None):
    """
    Find the shortest path whose transactions occur chronologically.

    Returns a dictionary suitable for backend consumption.
    """
    if not isinstance(source, str) or not source.strip():
        return {"success": False, "error": "Invalid source wallet."}

    if not isinstance(destination, str) or not destination.strip():
        return {"success": False, "error": "Invalid destination wallet."}

    source = source.strip()
    destination = destination.strip()

    if graph is None:
        try:
            graph = load_graph()
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            return {"success": False, "error": str(exc)}

    if source not in graph or destination not in graph:
        return {
            "success": False,
            "error": "Source or destination wallet was not found.",
            "source": source,
            "destination": destination,
        }

    if source == destination:
        return {
            "success": True,
            "source": source,
            "destination": destination,
            "path": [source],
            "transactions": [],
            "hops": 0,
        }

    try:
        earliest = (
            pd.to_datetime(start_time, utc=True)
            if start_time is not None
            else None
        )
    except (ValueError, TypeError):
        return {"success": False, "error": "Invalid start_time."}

    # BFS state stores the current wallet, path, transactions,
    # and the most recent transaction timestamp.
    queue = [(source, [source], [], earliest)]
    visited = {(source, None if earliest is None else earliest.value)}

    while queue:
        wallet, path, transactions, last_time = queue.pop(0)

        for next_wallet in graph.successors(wallet):
            if next_wallet in path:
                continue

            for edge in graph[wallet][next_wallet].values():
                tx_time = edge.get("timestamp")

                if tx_time is None or pd.isna(tx_time):
                    continue

                tx_time = pd.to_datetime(tx_time, utc=True)

                if last_time is not None and tx_time < last_time:
                    continue

                tx_record = {
                    "txid": edge.get("txid"),
                    "source": wallet,
                    "destination": next_wallet,
                    "timestamp": tx_time.isoformat(),
                }

                new_path = path + [next_wallet]
                new_transactions = transactions + [tx_record]

                if next_wallet == destination:
                    return {
                        "success": True,
                        "source": source,
                        "destination": destination,
                        "path": new_path,
                        "transactions": new_transactions,
                        "hops": len(new_path) - 1,
                    }

                state = (next_wallet, tx_time.value)

                if state not in visited:
                    visited.add(state)
                    queue.append(
                        (
                            next_wallet,
                            new_path,
                            new_transactions,
                            tx_time,
                        )
                    )

    return {
        "success": False,
        "error": "No chronological directed path found.",
        "source": source,
        "destination": destination,
    }