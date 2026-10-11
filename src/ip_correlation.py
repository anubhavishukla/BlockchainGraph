
import pandas as pd

transactions = pd.read_csv("data/transactions.csv")
network = pd.read_csv("data/network.csv")

transactions["txid"] = transactions["txid"].astype(str).str.strip()
network["txid"] = network["txid"].astype(str).str.strip()

print("IP -> TRANSACTION CORRELATION")
print("=============================")

# Match network records with transaction IDs
matched = network[
    network["txid"].isin(set(transactions["txid"]))
].copy()

print("Matched network records:", len(matched))
print("Unique matched transactions:", matched["txid"].nunique())

print("\nSample IP-to-transaction records:")
for _, row in matched.head(20).iterrows():
    print(
        f"TX: {row['txid']} | "
        f"{row['src_ip']}:{row['src_port']} -> "
        f"{row['dst_ip']}:{row['dst_port']} | "
        f"Country: {row['geo_country']} | "
        f"ASN: {row['asn']}"
    )

print("\nNetwork endpoint summary:")
for (src_ip, dst_ip), group in matched.groupby(["src_ip", "dst_ip"]):
    print(
        f"{src_ip} -> {dst_ip}: "
        f"{group['txid'].nunique()} unique transactions"
    )
