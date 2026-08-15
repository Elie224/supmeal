import pandas as pd

configs = {
    '2023-2024':  ('2024 (1) (1).xlsx', '2023 2024'),
    '2024-2025':  ('2025 (1) (1).xlsx', '2024 2025'),
    '2025-2026':  ('25 26.xlsx', '2025-2026'),
}

for label, (f, sh) in configs.items():
    path = r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES ' + f
    df = pd.read_excel(path, sheet_name=sh, header=None, skiprows=5)
    print(f'--- {label} (rows={len(df)}) ---')
    for col_idx, name in [(3, 'Salmonella'), (4, 'Listeria'), (5, 'STEC/RESA'), (6, 'RESA/AB')]:
        col = df.iloc[:, col_idx]
        numeric = pd.to_numeric(col, errors='coerce')
        non_null = numeric.dropna()
        print(f'  col{col_idx} {name}: n={len(non_null)} sum={non_null.sum():,.0f} max={non_null.max() if len(non_null) else 0}')
        # Look at non-numeric entries
        non_numeric = col[~col.apply(lambda x: isinstance(x, (int, float)) or pd.isna(x))].head(10).tolist()
        if non_numeric:
            print(f'    non-numeric samples: {non_numeric}')
