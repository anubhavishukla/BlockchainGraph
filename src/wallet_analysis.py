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


# Build the graph using the current dataset
for _, row in df.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    for wallet in inputs + outputs:
        G.add_node(wallet)

    for source in inputs:
        for destination in outputs:
            G.add_edge(source, destination, txid=row["txid"])


print("WALLET ANALYSIS")
print("================")
print("Total wallets/entities:", G.number_of_nodes())

for wallet in sorted(G.nodes()):
    print(
        f"Wallet: {wallet} | "
        f"Incoming: {G.in_degree(wallet)} | "
        f"Outgoing: {G.out_degree(wallet)} | "
        f"Total degree: {G.degree(wallet)}"
    )
