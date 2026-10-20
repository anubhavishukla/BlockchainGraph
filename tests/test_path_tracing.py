
import unittest
import networkx as nx
import pandas as pd

from src.path_tracing import trace_transaction_path


def create_test_graph():
    """Create a small graph with known transaction timestamps."""
    graph = nx.MultiDiGraph()

    graph.add_edge(
        "A", "B",
        txid="tx001",
        timestamp=pd.Timestamp("2026-01-01T10:00:00Z")
    )
    graph.add_edge(
        "B", "C",
        txid="tx002",
        timestamp=pd.Timestamp("2026-01-01T11:00:00Z")
    )
    graph.add_edge(
        "A", "C",
        txid="tx003",
        timestamp=pd.Timestamp("2026-01-01T12:00:00Z")
    )
    graph.add_edge(
        "C", "D",
        txid="tx004",
        timestamp=pd.Timestamp("2026-01-01T13:00:00Z")
    )

    return graph


class TestTransactionPath(unittest.TestCase):

    def setUp(self):
        self.graph = create_test_graph()

    def test_direct_path(self):
        result = trace_transaction_path("A", "B", self.graph)

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], ["A", "B"])
        self.assertEqual(result["hops"], 1)

    def test_multi_hop_path(self):
        result = trace_transaction_path("A", "D", self.graph)

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], ["A", "C", "D"])
        self.assertEqual(result["hops"], 2)

    def test_same_wallet(self):
        result = trace_transaction_path("A", "A", self.graph)

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], ["A"])
        self.assertEqual(result["hops"], 0)
        self.assertEqual(result["transactions"], [])

    def test_invalid_wallet(self):
        result = trace_transaction_path("A", "UNKNOWN", self.graph)

        self.assertFalse(result["success"])

    def test_reverse_path_not_found(self):
        result = trace_transaction_path("D", "A", self.graph)

        self.assertFalse(result["success"])

    def test_start_time_filter(self):
        result = trace_transaction_path(
            "A",
            "D",
            self.graph,
            start_time="2026-01-01T12:30:00Z"
        )

        self.assertFalse(result["success"])

    def test_transaction_timestamps_are_chronological(self):
        result = trace_transaction_path("A", "D", self.graph)

        self.assertTrue(result["success"])

        timestamps = [
            pd.to_datetime(tx["timestamp"], utc=True)
            for tx in result["transactions"]
        ]

        self.assertEqual(timestamps, sorted(timestamps))


if __name__ == "__main__":
    unittest.main(verbosity=2)
