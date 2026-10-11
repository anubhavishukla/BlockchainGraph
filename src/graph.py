
import pandas as pd
import networkx as nx

# Load transaction dataset
df = pd.read_csv("data/transactions.csv")

# Create a directed graph
G = nx.DiGraph()


def split_values(value):
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


# Build Wallet -> Transaction -> Wallet relationships
for _, row in df.iterrows():

    txid = str(row["txid"]).strip()
    transaction_node = f"TX_{txid}"

    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    # Add transaction node with its details
    G.add_node(
        transaction_node,
        node_type="transaction",
        timestamp=row["timestamp"]
    )

    # Connect input wallets to transaction
    for wallet in inputs:
        G.add_node(wallet, node_type="wallet")
        G.add_edge(wallet, transaction_node, relationship="input")

    # Connect transaction to output wallets
    for wallet in outputs:
        G.add_node(wallet, node_type="wallet")
        G.add_edge(transaction_node, wallet, relationship="output")


print("TRANSACTION GRAPH CREATED")
print("--------------------------")
print("Total nodes:", G.number_of_nodes())
print("Total connections:", G.number_of_edges())

wallet_nodes = [
    node for node, data in G.nodes(data=True)
    if data.get("node_type") == "wallet"
]

transaction_nodes = [
    node for node, data in G.nodes(data=True)
    if data.get("node_type") == "transaction"
]

print("Wallet nodes:", len(wallet_nodes))
print("Transaction nodes:", len(transaction_nodes))

print("\nSample relationships:")
for source, destination, data in list(G.edges(data=True))[:15]:
    print(
        f"{source} -> {destination} "
        f"| Relationship: {data['relationship']}"
    )
