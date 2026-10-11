
import pandas as pd
import networkx as nx

df = pd.read_csv("data/transactions.csv")
G = nx.MultiDiGraph()


def split_values(value):
    if pd.isna(value):
        return []
    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


# Build graph from current dataset
for _, row in df.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    for wallet in inputs + outputs:
        G.add_node(wallet)

    for source in inputs:
        for destination in outputs:
            G.add_edge(source, destination, txid=row["txid"])


# Wallet to investigate
wallet = input("Enter wallet ID (e.g. W500): ").strip()

if wallet not in G:
    print(f"Wallet '{wallet}' was not found in the graph.")
else:
    incoming = sorted(set(G.predecessors(wallet)))
    outgoing = sorted(set(G.successors(wallet)))
    connected = sorted(set(incoming + outgoing))

    print("\nCONNECTED WALLET ANALYSIS")
    print("=========================")
    print("Wallet:", wallet)
    print("Incoming wallets:", incoming)
    print("Outgoing wallets:", outgoing)
    print("All connected wallets:", connected)
