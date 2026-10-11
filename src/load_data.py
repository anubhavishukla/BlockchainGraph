import pandas as pd

# Location of our transaction dataset
file_path = "data/transactions.csv"

# Read CSV file
df = pd.read_csv(file_path)

# Display the data
print("Transaction Data:")
print(df)

# Display column names
print("\nColumns:")
print(df.columns.tolist())

# Display number of transactions
print("\nNumber of transactions:", len(df))