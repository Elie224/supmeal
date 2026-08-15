import pandas as pd

files = {
    '2024': r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES 2024 (1) (1).xlsx',
    '2025': r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES 2025 (1) (1).xlsx',
    '25_26': r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES 25 26.xlsx',
}

for label, f in files.items():
    print('=' * 80)
    print(f'FICHIER: {label}')
    print('=' * 80)
    xls = pd.ExcelFile(f)
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh, header=None)
        print(f'\n--- Sheet: {sh!r} ({df.shape[0]} rows x {df.shape[1]} cols) ---')
        print(df.head(25).to_string(max_cols=df.shape[1]))
