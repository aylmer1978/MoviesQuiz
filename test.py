import pandas as pd

df = pd.read_csv("direct-to-video-horror-cinema.csv")
for i, row in df.iterrows():
    print(i, type(i))              # debe ser int
    print(row['Name'])             # debe ser str
    print(len(df), type(len(df)))  # len debe ser int
    break