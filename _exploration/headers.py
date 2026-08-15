import pandas as pd

files = {
    '2024_main': ('2024 (1) (1).xlsx', '2023 2024'),
    '2024_f1':    ('2024 (1) (1).xlsx', 'Feuil1'),
    '2024_f2':    ('2024 (1) (1).xlsx', 'Feuil2'),
    '2024_f3':    ('2024 (1) (1).xlsx', 'Feuil3'),
    '2025_main':  ('2025 (1) (1).xlsx', '2024 2025'),
    '2025_f2':    ('2025 (1) (1).xlsx', 'Feuil2'),
    '2025_f3':    ('2025 (1) (1).xlsx', 'Feuil3'),
    '25_26_main': ('25 26.xlsx', '2025-2026'),
    '25_26_f2':   ('25 26.xlsx', 'Feuil2'),
    '25_26_f3':   ('25 26.xlsx', 'Feuil3'),
}

for label, (f, sh) in files.items():
    path = r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES ' + f
    print('=' * 80)
    print(f'=== {label} ({sh}) ===')
    print('=' * 80)
    df = pd.read_excel(path, sheet_name=sh, header=None)
    print(f'shape={df.shape}')
    # Show rows 0..6 to capture headers
    for i in range(min(8, len(df))):
        row = df.iloc[i].tolist()
        # Compact print
        print(f'  R{i}:', row)
