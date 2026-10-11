
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from itertools import combinations

# ==========================================
# 1. LOAD ALL THREE DATASETS
# ==========================================

transactions = pd.read_csv("data/transactions.csv")
labels = pd.read_csv("data/labels.csv")
network = pd.read_csv("data/network.csv")

required_tx = [
    "timestamp", "txid", "input_addresses", "output_addresses",
    "input_amounts", "output_amounts", "fee", "script_type"
]
required_labels = ["entity_id", "pattern_type", "label"]
required_network = [
    "timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
    "txid", "geo_country", "asn"
]

for name, df, required in [
    ("transactions.csv", transactions, required_tx),
    ("labels.csv", labels, required_labels),
    ("network.csv", network, required_network)
]:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {missing}")

transactions = transactions.dropna(
    subset=["txid", "input_addresses", "output_addresses"]
).copy()

transactions["txid"] = transactions["txid"].astype(str).str.strip()
labels["entity_id"] = labels["entity_id"].astype(str).str.strip()
network["txid"] = network["txid"].astype(str).str.strip()

print("\n===================================")
print("   BLOCKCHAIN GRAPH INVESTIGATOR")
print("===================================")
print("Transactions:", len(transactions))
print("Label records:", len(labels))
print("Network records:", len(network))


# ==========================================
# 2. PREPARE LABELS AND NETWORK DATA
# ==========================================

label_lookup = (
    labels.drop_duplicates("entity_id", keep="last")
    .set_index("entity_id")[["pattern_type", "label"]]
    .to_dict("index")
)

# One transaction can have multiple network records.
network_lookup = {
    txid: group.to_dict("records")
    for txid, group in network.groupby("txid")
}

transaction_ids = set(transactions["txid"])
network_ids = set(network["txid"])

matched_ids = transaction_ids & network_ids

print("\n===================================")
print("DATASET LINKING")
print("===================================")
print("Transactions matched with network data:", len(matched_ids))
print("Transactions without network data:",
      len(transaction_ids - network_ids))


# ==========================================
# 3. BUILD MULTI-TRANSACTION WALLET GRAPH
# ==========================================

def split_values(value):
    """Split pipe-separated wallet addresses or amounts."""
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


G = nx.MultiDiGraph()

# Explicit Wallet -> Transaction -> Wallet graph
G_tx = nx.DiGraph()

for _, row in transactions.iterrows():
    txid = str(row["txid"]).strip()
    tx_node = f"TX_{txid}"

    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    # Add transaction node
    G_tx.add_node(
        tx_node,
        node_type="transaction",
        timestamp=str(row["timestamp"])
    )

    # Wallet -> Transaction
    for wallet in inputs:
        G_tx.add_node(wallet, node_type="wallet")
        G_tx.add_edge(
            wallet,
            tx_node,
            relationship="input"
        )

    # Transaction -> Wallet
    for wallet in outputs:
        G_tx.add_node(wallet, node_type="wallet")
        G_tx.add_edge(
            tx_node,
            wallet,
            relationship="output"
        )

# Attach classification labels to wallet nodes
for node, attributes in G_tx.nodes(data=True):
    if attributes.get("node_type") == "wallet":
        info = label_lookup.get(node, {})
        attributes["pattern_type"] = info.get(
            "pattern_type", "unlabelled"
        )
        attributes["label"] = info.get("label", "unlabelled")

wallet_count = sum(
    1 for _, d in G_tx.nodes(data=True)
    if d.get("node_type") == "wallet"
)

transaction_count = sum(
    1 for _, d in G_tx.nodes(data=True)
    if d.get("node_type") == "transaction"
)

print("\nEXPLICIT TRANSACTION GRAPH")
print("==========================")
print("Total nodes:", G_tx.number_of_nodes())
print("Wallet nodes:", wallet_count)
print("Transaction nodes:", transaction_count)
print("Total connections:", G_tx.number_of_edges())


for _, row in transactions.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    txid = row["txid"]
    network_records = network_lookup.get(txid, [])

    # Add all input/output addresses as individual wallet nodes.
    for wallet in inputs + outputs:
        G.add_node(wallet)

    # Model possible relationships within a transaction.
    # This does not claim exact input-to-output fund allocation.
    for source in inputs:
        for destination in outputs:
            G.add_edge(
                source,
                destination,
                key=txid,
                txid=txid,
                timestamp=str(row["timestamp"]),
                input_amounts=str(row["input_amounts"]),
                output_amounts=str(row["output_amounts"]),
                fee=str(row["fee"]),
                script_type=str(row["script_type"]),
                network_records=network_records
            )

# Attach available classification labels to graph nodes.
for wallet in G.nodes():
    info = label_lookup.get(wallet, {})
    G.nodes[wallet]["pattern_type"] = info.get("pattern_type", "unlabelled")
    G.nodes[wallet]["label"] = info.get("label", "unlabelled")

print("\n===================================")
print("GRAPH SUMMARY")
print("===================================")
print("Wallet/entity nodes:", G.number_of_nodes())
print("Possible transaction connections:", G.number_of_edges())


# ==========================================
# 4. WALLET DEGREE ANALYSIS
# ==========================================

print("\n===================================")
print("WALLET ANALYSIS")
print("===================================")

for wallet in sorted(G.nodes()):
    incoming = G.in_degree(wallet)
    outgoing = G.out_degree(wallet)

    print(
        f"{wallet} -> Incoming: {incoming}, "
        f"Outgoing: {outgoing}, Degree: {G.degree(wallet)}, "
        f"Label: {G.nodes[wallet]['label']}"
    )

if G.number_of_nodes() > 0:
    highest_degree_wallet = max(G.nodes(), key=lambda w: G.degree(w))

    print("\nHighest-degree entity:", highest_degree_wallet)
    print("Its label:", G.nodes[highest_degree_wallet]["label"])


# ==========================================
# 5. LABEL-BASED SUSPICIOUS ENTITY ANALYSIS
# ==========================================

print("\n===================================")
print("SUSPICIOUS ENTITY ANALYSIS")
print("===================================")

suspicious_entities = set(
    labels.loc[labels["label"].str.lower() == "suspicious", "entity_id"]
)
normal_entities = set(
    labels.loc[labels["label"].str.lower() == "normal", "entity_id"]
)

suspicious_in_graph = sorted(suspicious_entities & set(G.nodes()))
normal_in_graph = sorted(normal_entities & set(G.nodes()))

print("Suspicious entities in graph:", len(suspicious_in_graph))
print("Normal entities in graph:", len(normal_in_graph))
print("Suspicious entity IDs:", suspicious_in_graph)
print("Normal entity IDs:", normal_in_graph)

unmatched_suspicious = sorted(suspicious_entities - set(G.nodes()))
print("Suspicious labels not present as graph nodes:", unmatched_suspicious)


# ==========================================
# 6. PATH INVESTIGATION
# ==========================================

print("\n===================================")
print("SUSPICIOUS ENTITY PATH INVESTIGATION")
print("===================================")

paths_found = 0

for source, destination in combinations(suspicious_in_graph, 2):
    if nx.has_path(G, source, destination):
        path = nx.shortest_path(G, source, destination)
        print(f"{source} -> {destination}: {' -> '.join(path)}")
        paths_found += 1

    if paths_found >= 5:
        break

if paths_found == 0:
    print("No directed path found between the checked suspicious entities.")


# ==========================================
# 7. IP / NETWORK CORRELATION
# ==========================================

print("\n===================================")
print("IP TO TRANSACTION CORRELATION")
print("===================================")

network_transactions = network[
    network["txid"].isin(transaction_ids)
]

print("Matched network records:", len(network_transactions))
print("Unique matched transactions:", network_transactions["txid"].nunique())

# Show a small sample instead of printing every network record.
for _, row in network_transactions.head(10).iterrows():
    print(
        f"TX: {row['txid']} | "
        f"{row['src_ip']}:{row['src_port']} -> "
        f"{row['dst_ip']}:{row['dst_port']} | "
        f"Country: {row['geo_country']} | ASN: {row['asn']}"
    )


# ==========================================
# 8. TRANSACTIONS INVOLVING SUSPICIOUS ENTITIES
# ==========================================

print("\n===================================")
print("SUSPICIOUS TRANSACTION INVESTIGATION")
print("===================================")

suspicious_transactions = []

for _, row in transactions.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    involved = sorted(
        (set(inputs) | set(outputs)) & suspicious_entities
    )

    if involved:
        suspicious_transactions.append((row, involved))

print("Transactions involving labelled suspicious entities:",
      len(suspicious_transactions))

for row, involved in suspicious_transactions[:10]:
    txid = row["txid"]
    print(
        f"{txid} | Entities: {', '.join(involved)} | "
        f"Type: {row['script_type']} | "
        f"Network records: {len(network_lookup.get(txid, []))}"
    )


# ==========================================
# 9. FINAL INVESTIGATION SUMMARY
# ==========================================

print("\n===================================")
print("INVESTIGATION SUMMARY")
print("===================================")

print("Transactions analysed:", len(transactions))
print("Wallet/entity nodes:", G.number_of_nodes())
print("Possible transaction connections:", G.number_of_edges())
print("Suspicious entities matched:", len(suspicious_in_graph))
print("Normal entities matched:", len(normal_in_graph))
print("Transactions linked to network data:", len(matched_ids))
print("Transactions involving suspicious labels:",
      len(suspicious_transactions))

print("\nBlockchain graph investigation completed.")

# Interactive Wallet Graph Visualization
import plotly.graph_objects as go

# Create graph layout
pos = nx.spring_layout(G, seed=42)

edge_x = []
edge_y = []

for source, target in G.edges():
    x0, y0 = pos[source]
    x1, y1 = pos[target]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])

edge_trace = go.Scatter(
    x=edge_x,
    y=edge_y,
    mode="lines",
    line=dict(width=1, color="gray"),
    hoverinfo="none"
)

node_x = []
node_y = []
node_text = []
node_colors = []

for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)

    label = G.nodes[node].get("label", "unlabelled")
    node_text.append(f"Entity: {node}<br>Label: {label}")

    if label == "suspicious":
        node_colors.append("red")
    elif label == "normal":
        node_colors.append("green")
    else:
        node_colors.append("gray")

node_trace = go.Scatter(
    x=node_x,
    y=node_y,
    mode="markers",
    hoverinfo="text",
    text=node_text,
    marker=dict(
        size=10,
        color=node_colors,
        line=dict(width=1, color="white")
    )
)

fig = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title="Blockchain Wallet Connection Graph",
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
)

fig.write_html("blockchain_graph.html")
print("Interactive graph saved as blockchain_graph.html")
