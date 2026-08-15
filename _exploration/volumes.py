import pandas as pd

# Verify the volume numbers the user cited
configs = {
    '2023-2024':  ('2024 (1) (1).xlsx', '2023 2024'),
    '2024-2025':  ('2025 (1) (1).xlsx', '2024 2025'),
    '2025-2026':  ('25 26.xlsx', '2025-2026'),
}

print(f'{"Campagne":<12} {"Salmonella":>12} {"Listeria":>12} {"STEC":>12} {"RESA":>12} {"Total":>12}')
for label, (f, sh) in configs.items():
    path = r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES ' + f
    df = pd.read_excel(path, sheet_name=sh, header=None, skiprows=5)
    # Salmonella col 3, Listeria col 4, STEC col 5 (only in 25-26), RESA col 6 (antibiotiques)
    s = pd.to_numeric(df.iloc[:, 3], errors='coerce').sum()
    l = pd.to_numeric(df.iloc[:, 4], errors='coerce').sum()
    # STEC only in 25-26 (col 5)
    try:
        stec = pd.to_numeric(df.iloc[:, 5], errors='coerce').sum()
    except:
        stec = 0
    # RESA / antibio
    try:
        resa = pd.to_numeric(df.iloc[:, 6], errors='coerce').sum()
    except:
        resa = 0
    total = s + l + stec + resa
    print(f'{label:<12} {s:>12,.0f} {l:>12,.0f} {stec:>12,.0f} {resa:>12,.0f} {total:>12,.0f}')
