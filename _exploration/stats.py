import pandas as pd
import re

# Read main sheet of each file (the most complete one)
configs = {
    '2024':  ('2024 (1) (1).xlsx', '2023 2024'),
    '2025':  ('2025 (1) (1).xlsx', '2024 2025'),
    '25_26': ('25 26.xlsx', '2025-2026'),
}

for label, (f, sh) in configs.items():
    path = r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES ' + f
    df = pd.read_excel(path, sheet_name=sh, header=None, skiprows=5)
    # Try to extract producer name from col 0
    col0 = df.iloc[:, 0].astype(str).str.strip()
    # Tour/Route from col 10
    col10 = df.iloc[:, 10]
    
    print('=' * 60)
    print(f'=== {label} ===')
    print(f'Rows after header skip: {len(df)}')
    # Number of rows with producer info
    non_null = col0[col0 != 'nan'].dropna()
    print(f'Non-empty col0 rows: {len(non_null)}')
    # Rows starting with TOURNE
    tournees = col0[col0.str.contains('TOURNEE', case=False, na=False)]
    print(f'TOURNEE rows: {len(tournees)}')
    print('Sample tournees:', tournees.head(10).tolist())
    # Distinct producer names (filter out TOURNEE)
    producers = col0[~col0.str.contains('TOURNEE', case=False, na=False)]
    producers = producers[producers != 'nan']
    producers = producers[producers != 'SALMONELLE']
    producers = producers[producers != 'CAMPAGNE  2023- 2024']
    producers = producers[producers != 'CAMPAGNE 2025']
    producers = producers[producers != 'CAMPAGNE  25 26']
    producers = producers[producers != 'Bleu Recherche Allaitantes']
    producers = producers[producers != 'DECLASSEMENTS PATHOGENES ET ANALYSES GENEREES']
    producers = producers[producers != '']
    unique = producers.unique()
    print(f'Unique producers: {len(unique)}')
    print('Sample producers:', unique[:30].tolist())
    # Pathogen counts
    for pcol in [3, 4, 5, 6, 7]:
        non_null_p = df.iloc[:, pcol].dropna()
        if len(non_null_p) > 0:
            print(f'  col{pcol} non-null:', len(non_null_p), 'sample:', non_null_p.head(5).tolist())
