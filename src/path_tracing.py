
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


# Build graph from the current dataset
for _, row in df.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    for wallet in inputs + outputs:
        G.add_node(wallet)

    for source in inputs:
        for destination in outputs:
            G.add_edge(source, destination, txid=row["txid"])


source = input("Enter source wallet (e.g. W500): ").strip()
destination = input("Enter destination wallet (e.g. W505): ").strip()

print("\nTRANSACTION PATH ANALYSIS")
print("=========================")
print(f"Source wallet: {source}")
print(f"Destination wallet: {destination}")

if source not in G or destination not in G:
    print("Source or destination wallet was not found in the graph.")
elif nx.has_path(G, source, destination):
    path = nx.shortest_path(G, source, destination)
    print("\nShortest possible transaction path:")
    print(" -> ".join(path))
    print("Number of hops:", len(path) - 1)
else:
    print("\nNo directed path found.")
