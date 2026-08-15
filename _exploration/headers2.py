import pandas as pd
files = {
    '2025_main':  ('2025 (1) (1).xlsx', '2024 2025'),
    '25_26_main': ('25 26.xlsx', '2025-2026'),
}
for label, (f, sh) in files.items():
    path = r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES ' + f
    print('=' * 80)
    print(f'=== {label} ({sh}) ===')
    df = pd.read_excel(path, sheet_name=sh, header=None)
    print(f'shape={df.shape}')
    for i in range(min(8, len(df))):
        row = df.iloc[i].tolist()
        print(f'  R{i}:', row)
