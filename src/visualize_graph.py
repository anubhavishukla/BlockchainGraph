
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# =====================================================
# 1. LOAD DATA
# =====================================================
tx = pd.read_csv("data/transactions.csv")
labels_df = pd.read_csv("data/labels.csv")

G = nx.DiGraph()


def split_values(value):
    if pd.isna(value):
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


# =====================================================
# 2. BUILD WALLET -> TRANSACTION -> WALLET NETWORK
# =====================================================
G = nx.DiGraph()

label_lookup = (
    labels_df.drop_duplicates("entity_id", keep="last")
    .set_index("entity_id")["label"]
    .to_dict()
)

for _, row in tx.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])
    txid = str(row["txid"]).strip()
    tx_node = f"TX_{txid}"

    # Add transaction node
    G.add_node(
        tx_node,
        node_type="transaction",
        label="transaction",
        txid=txid
    )

    # Wallet -> Transaction
    for wallet in inputs:
        G.add_node(
            wallet,
            node_type="wallet",
            label=label_lookup.get(wallet, "unlabelled")
        )
        G.add_edge(wallet, tx_node, relationship="input")

    # Transaction -> Wallet
    for wallet in outputs:
        G.add_node(
            wallet,
            node_type="wallet",
            label=label_lookup.get(wallet, "unlabelled")
        )
        G.add_edge(tx_node, wallet, relationship="output")


# =====================================================
# 3. INVESTIGATION PATH
# =====================================================
source_wallet = "W500"
destination_wallet = "W505"

# Find a wallet route using wallet-to-wallet relationships
wallet_graph = nx.DiGraph()

for _, row in tx.iterrows():
    inputs = split_values(row["input_addresses"])
    outputs = split_values(row["output_addresses"])

    for source in inputs:
        for target in outputs:
            if source != target:
                wallet_graph.add_edge(source, target)

if (
    source_wallet in wallet_graph
    and destination_wallet in wallet_graph
    and nx.has_path(wallet_graph, source_wallet, destination_wallet)
):
    wallet_path = nx.shortest_path(
        wallet_graph, source_wallet, destination_wallet
    )
else:
    wallet_path = []

# Convert wallet route into an alternating wallet/transaction path
path = []

for i, wallet in enumerate(wallet_path):
    path.append(wallet)

    if i < len(wallet_path) - 1:
        next_wallet = wallet_path[i + 1]

        # Find a transaction linking these two wallets
        matching_tx = None

        for _, row in tx.iterrows():
            inputs = split_values(row["input_addresses"])
            outputs = split_values(row["output_addresses"])

            if wallet in inputs and next_wallet in outputs:
                matching_tx = f"TX_{str(row['txid']).strip()}"
                break

        if matching_tx:
            path.append(matching_tx)

path_nodes = set(path)
path_edges = set(zip(path, path[1:]))

print(
    "Investigation path:",
    " -> ".join(path) if path else "No path found"
)
# =====================================================
# 4. 3D LAYOUT
# =====================================================
pos = nx.spring_layout(
    G,
    dim=3,
    seed=42,
    k=2.5,
    iterations=200
)

fig = go.Figure()

# =====================================================
# 5. CONNECTIONS
# =====================================================
ex, ey, ez = [], [], []

for u, v in G.edges():
    x0, y0, z0 = pos[u]
    x1, y1, z1 = pos[v]

    ex.extend([x0, x1, None])
    ey.extend([y0, y1, None])
    ez.extend([z0, z1, None])

fig.add_trace(go.Scatter3d(
    x=ex, y=ey, z=ez,
    mode="lines",
    line=dict(color="rgba(94,145,190,0.22)", width=1),
    hoverinfo="skip",
    name="Wallet connections"
))

# =====================================================
# 6. GLOWING INVESTIGATION PATH
# =====================================================
px, py, pz = [], [], []

for u, v in path_edges:
    x0, y0, z0 = pos[u]
    x1, y1, z1 = pos[v]

    px.extend([x0, x1, None])
    py.extend([y0, y1, None])
    pz.extend([z0, z1, None])

if path_edges:
    # Outer glow
    fig.add_trace(go.Scatter3d(
        x=px, y=py, z=pz,
        mode="lines",
        line=dict(color="rgba(0,225,255,0.18)", width=12),
        hoverinfo="skip",
        showlegend=False
    ))

    # Inner glow
    fig.add_trace(go.Scatter3d(
        x=px, y=py, z=pz,
        mode="lines",
        line=dict(color="rgba(0,225,255,0.55)", width=6),
        hoverinfo="skip",
        showlegend=False
    ))

    # Bright core
    fig.add_trace(go.Scatter3d(
        x=px, y=py, z=pz,
        mode="lines",
        line=dict(color="#42F5FF", width=3),
        hoverinfo="skip",
        name="Investigation path"
    ))


# =====================================================
# 7. NODE CATEGORIES AND HOVER DETAILS
# =====================================================
categories = {
    "Investigation path": {"color": "#42F5FF", "size": 8},
    "Suspicious wallets": {"color": "#FF5268", "size": 6},
    "Normal wallets": {"color": "#32E6B5", "size": 5},
    "Unlabelled wallets": {"color": "#8295B0", "size": 4},
    "Transaction nodes": {"color": "#B68CFF", "size": 4}
}

groups = {name: [] for name in categories}

for node, data in G.nodes(data=True):
    node_type = data.get("node_type", "wallet")

    if node in path_nodes:
        category = "Investigation path"
    elif node_type == "transaction":
        category = "Transaction nodes"
    elif data.get("label") == "suspicious":
        category = "Suspicious wallets"
    elif data.get("label") == "normal":
        category = "Normal wallets"
    else:
        category = "Unlabelled wallets"

    groups[category].append(node)

for category, nodes in groups.items():
    if not nodes:
        continue

    xs, ys, zs, hover = [], [], [], []
    text_labels = []

    for node in nodes:
        x, y, z = pos[node]
        data = G.nodes[node]
        node_type = data.get("node_type", "wallet")

        xs.append(x)
        ys.append(y)
        zs.append(z)

        if node_type == "transaction":
            hover.append(
                f"<b>TRANSACTION</b><br>"
                f"Transaction ID: {data.get('txid', node)}<br>"
                f"Incoming wallets: {G.in_degree(node)}<br>"
                f"Outgoing wallets: {G.out_degree(node)}"
            )
        else:
            hover.append(
                f"<b>WALLET: {node}</b><br>"
                f"Category: {category}<br>"
                f"Dataset label: {data.get('label', 'unlabelled')}<br>"
                f"Incoming connections: {G.in_degree(node)}<br>"
                f"Outgoing connections: {G.out_degree(node)}<br>"
                f"Total degree: {G.degree(node)}"
            )

        text_labels.append(
            node if node in path_nodes else ""
        )

    fig.add_trace(go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode=(
            "markers+text"
            if category == "Investigation path"
            else "markers"
        ),
        text=(
            text_labels
            if category == "Investigation path"
            else None
        ),
        textposition="top center",
        textfont=dict(
            family="Arial",
            size=10,
            color="#FFFFFF"
        ),
        name=f"{category} ({len(nodes)})",
        marker=dict(
            size=categories[category]["size"],
            color=categories[category]["color"],
            opacity=0.95,
            line=dict(
                color=categories[category]["color"],
                width=1.5
            ),
            symbol=(
                "diamond"
                if category == "Transaction nodes"
                else "circle"
            )
        ),
        hovertext=hover,
        hoverinfo="text"
    ))


# =====================================================
# 8. DASHBOARD STATISTICS
# =====================================================
total_wallets = sum(
    1 for _, data in G.nodes(data=True)
    if data.get("node_type") == "wallet"
)

total_transaction_nodes = sum(
    1 for _, data in G.nodes(data=True)
    if data.get("node_type") == "transaction"
)

total_connections = G.number_of_edges()
total_transactions = len(tx)

suspicious_count = sum(
    1 for _, data in G.nodes(data=True)
    if data.get("node_type") == "wallet"
    and data.get("label") == "suspicious"
)

cards = [
    (0.02, 0.235, "TOTAL WALLETS",
     f"{total_wallets}", "#42F5FF"),
    (0.265, 0.48, "TRANSACTION NODES",
     f"{total_transaction_nodes}", "#B68CFF"),
    (0.51, 0.725, "SUSPICIOUS-LABELLED",
     f"{suspicious_count}", "#FF5268"),
    (0.755, 0.97, "CONNECTIONS",
     f"{total_connections}", "#32E6B5")
]

for x0, x1, label, value, accent in cards:
    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=x0, x1=x1, y0=1.025, y1=1.17,
        line=dict(color=accent, width=1),
        fillcolor="#111B2B",
        layer="below"
    )

    fig.add_annotation(
        x=(x0 + x1) / 2,
        y=1.135,
        xref="paper", yref="paper",
        text=f"<b>{label}</b>",
        showarrow=False,
        font=dict(size=10, color="#A9BCD2"),
        xanchor="center"
    )

    fig.add_annotation(
        x=(x0 + x1) / 2,
        y=1.075,
        xref="paper", yref="paper",
        text=f"<b>{value}</b>",
        showarrow=False,
        font=dict(size=23, color=accent),
        xanchor="center"
    )

# =====================================================
# 9. PREMIUM CYBERSECURITY DASHBOARD
# =====================================================
fig.update_layout(
    title=dict(
        text=(
            "<b>â—ˆ TRANSACTION INTELLIGENCE</b>"
            "<br><sup>BLOCKCHAIN GRAPH INVESTIGATION"
            " &nbsp; | &nbsp; INTERACTIVE 3D NETWORK</sup>"
        ),
        x=0.02,
        y=0.98,
        xanchor="left",
        font=dict(
            family="Arial",
            size=23,
            color="#EDF7FF"
        )
    ),

    paper_bgcolor="#080D17",
    font=dict(
        family="Arial",
        color="#DCEBFA"
    ),

    height=900,
    margin=dict(l=10, r=10, t=200, b=15),

    showlegend=True,
    legend=dict(
        title=dict(text="NETWORK LEGEND"),
        bgcolor="rgba(14,24,39,0.92)",
        bordercolor="#273B54",
        borderwidth=1,
        font=dict(size=11, color="#DCEBFA"),
        x=0.015,
        y=0.98,
        xanchor="left",
        yanchor="top"
    ),

    hoverlabel=dict(
        bgcolor="#111D30",
        bordercolor="#42F5FF",
        font=dict(
            family="Arial",
            size=13,
            color="#FFFFFF"
        )
    ),

    scene=dict(
        bgcolor="#0A1322",
        aspectmode="data",
        dragmode="orbit",
        camera=dict(
            eye=dict(x=1.65, y=1.65, z=1.25),
            projection=dict(type="perspective")
        ),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        zaxis=dict(visible=False)
    )
)

# =====================================================
# 10. EXPORT
# =====================================================
output_file = "blockchain_graph_3d.html"

# =====================================================
# 10. CINEMATIC WEBPAGE DESIGN + EXPORT
# =====================================================
import os
import webbrowser

output_file = "blockchain_graph_3d.html"

# First generate the fully interactive Plotly graph
fig.write_html(
    output_file,
    include_plotlyjs=True,
    auto_open=False
)

# Add a custom artistic webpage around the graph
with open(output_file, "r", encoding="utf-8") as file:
    html = file.read()

art_css = """
<style>
* { box-sizing: border-box; }

html {
    background: #050812;
    scroll-behavior: smooth;
}

body {
    margin: 0;
    color: #e8f4ff;
    background:
        radial-gradient(ellipse at 12% 8%, rgba(0,180,255,.12), transparent 34%),
        radial-gradient(ellipse at 88% 18%, rgba(115,60,255,.12), transparent 32%),
        linear-gradient(145deg, #050812, #091222 55%, #060913);
    font-family: "Segoe UI", Arial, sans-serif;
    overflow-x: hidden;
    min-height: 100vh;
}

/* Subtle technical grid */
body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: .20;
    background-image:
        linear-gradient(rgba(91,164,220,.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(91,164,220,.08) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: linear-gradient(to bottom, black, transparent 90%);
}

/* Ambient light */
body::after {
    content: "";
    position: fixed;
    width: 360px;
    height: 360px;
    right: -180px;
    top: 30%;
    border-radius: 50%;
    background: rgba(0,210,255,.08);
    filter: blur(100px);
    pointer-events: none;
    z-index: 0;
}

.page-header {
    position: relative;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 25px clamp(18px, 4vw, 58px) 20px;
    border-bottom: 1px solid rgba(120,180,230,.15);
    background: rgba(6,12,24,.65);
    backdrop-filter: blur(18px);
}

.brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.brand-icon {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    border-radius: 15px;
    color: #69f4ff;
    font-size: 25px;
    background: linear-gradient(145deg, #122b43, #101329);
    border: 1px solid rgba(66,245,255,.45);
    box-shadow: 0 0 26px rgba(66,245,255,.12);
}

.brand-name {
    margin: 0;
    font-size: clamp(18px, 2vw, 25px);
    font-weight: 750;
    letter-spacing: 1.5px;
}

.brand-subtitle {
    margin-top: 5px;
    color: #8da8c4;
    font-size: 11px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
}

.status-pill {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 15px;
    border-radius: 30px;
    border: 1px solid rgba(50,230,181,.28);
    background: rgba(50,230,181,.07);
    color: #76f5ca;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    white-space: nowrap;
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #32e6b5;
    box-shadow: 0 0 12px #32e6b5;
}

.intro {
    position: relative;
    z-index: 1;
    padding: 26px clamp(18px, 4vw, 58px) 0;
}

.eyebrow {
    color: #52e9f8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
}

.intro h2 {
    margin: 10px 0 8px;
    font-size: clamp(22px, 3vw, 36px);
    letter-spacing: -.7px;
    font-weight: 650;
}

.intro p {
    margin: 0;
    max-width: 760px;
    color: #8da4bf;
    font-size: 14px;
    line-height: 1.8;
}

.graph-shell {
    position: relative;
    z-index: 1;
    margin: 10px clamp(8px, 2vw, 28px) 0;
    border: 1px solid rgba(94,170,225,.19);
    border-radius: 22px;
    overflow: hidden;
    background: rgba(9,17,31,.72);
    box-shadow:
        0 25px 90px rgba(0,0,0,.30),
        0 0 45px rgba(0,190,255,.045),
        inset 0 1px rgba(255,255,255,.035);
}

.plotly-graph-div {
    width: 100% !important;
}

.investigation-strip {
    position: relative;
    z-index: 1;
    margin: 18px clamp(18px, 4vw, 58px) 0;
    padding: 19px 22px;
    border: 1px solid rgba(66,245,255,.22);
    border-radius: 16px;
    background: linear-gradient(110deg,
        rgba(19,49,68,.62),
        rgba(16,21,44,.72));
    box-shadow: inset 0 1px rgba(255,255,255,.04);
}

.strip-label {
    color: #7f9bb9;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 12px;
}

.path {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 9px;
}

.wallet-chip {
    padding: 8px 12px;
    border-radius: 9px;
    border: 1px solid rgba(66,245,255,.30);
    background: rgba(66,245,255,.07);
    color: #a4f9ff;
    font: 600 12px Consolas, monospace;
}

.path-arrow {
    color: #42f5ff;
    font-size: 17px;
}

.footer {
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
    margin-top: 25px;
    padding: 20px clamp(18px, 4vw, 58px) 25px;
    border-top: 1px solid rgba(120,180,230,.12);
    color: #7187a1;
    font-size: 11px;
    letter-spacing: .4px;
}

.footer strong {
    color: #9eb8d1;
}

@media (max-width: 600px) {
    .page-header { align-items: flex-start; }
    .brand-subtitle { letter-spacing: 1px; }
    .status-pill { font-size: 9px; padding: 8px; }
    .brand-icon { width: 40px; height: 40px; }
    .investigation-strip { padding: 15px; }
}
</style>
"""

header = """
<header class="page-header">
  <div class="brand">
    <div class="brand-icon">&#9672;</div>
    <div>
      <h1 class="brand-name">VYON <span style="color:#52e9f8">INTELLIGENCE</span></h1>
      <div class="brand-subtitle">Blockchain investigation system</div>
    </div>
  </div>
  <div class="status-pill">
    <span class="status-dot"></span>
    ANALYSIS READY
  </div>
</header>

<section class="intro">
  <div class="eyebrow">NETWORK FORENSICS / 3D EXPLORER</div>
  <h2>See the connections. Trace the network.</h2>
  <p>
    Explore wallet relationships, inspect entity labels and follow
    the selected transaction path through an interactive 3D network.
  </p>
</section>

<div class="graph-shell">
"""

footer = """
</div>

<section class="investigation-strip">
  <div class="strip-label">SELECTED INVESTIGATION PATH</div>
  <div class="path">
    <span class="wallet-chip">W500</span>
    <span class="path-arrow">&#8594;</span>
    <span class="wallet-chip">W501</span>
    <span class="path-arrow">&#8594;</span>
    <span class="wallet-chip">W502</span>
    <span class="path-arrow">&#8594;</span>
    <span class="wallet-chip">W503</span>
    <span class="path-arrow">&#8594;</span>
    <span class="wallet-chip">W504</span>
    <span class="path-arrow">&#8594;</span>
    <span class="wallet-chip">W505</span>
  </div>
</section>

<footer class="footer">
  <span><strong>VYON INTELLIGENCE</strong> &nbsp;|&nbsp; Academic graph analysis</span>
  <span>Dataset-based investigation Â· Interactive 3D visualization</span>
</footer>
"""

# Inject the visual theme and webpage sections
html = html.replace("</head>", art_css + "\n</head>", 1)
html = html.replace("<body>", "<body>\n" + header, 1)
html = html.replace("</body>", footer + "\n</body>", 1)

with open(output_file, "w", encoding="utf-8") as file:
    file.write(html)

print(f"Artistic 3D dashboard saved to {output_file}")
print("Interactive graph and webpage design are ready.")

webbrowser.open_new_tab(
    "file://" + os.path.abspath(output_file).replace("\\", "/")
)

