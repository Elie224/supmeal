import pandas as pd

configs = {
    '2023-2024':  ('2024 (1) (1).xlsx', '2023 2024'),
    '2024-2025':  ('2025 (1) (1).xlsx', '2024 2025'),
    '2025-2026':  ('25 26.xlsx', '2025-2026'),
}

# Use the AGGREGATED TOTAL rows (max value per pathogen column)
print(f'{"Campagne":<12} {"Salmonella":>12} {"Listeria":>12} {"STEC":>10} {"RESA/AB":>10} {"Total":>12}  %Salmo')
totals = {'Salmonella':0, 'Listeria':0, 'STEC':0, 'RESA':0}
for label, (f, sh) in configs.items():
    path = r'C:\Users\KOURO\Downloads\RECAP LAITS DECLASSES ' + f
    df = pd.read_excel(path, sheet_name=sh, header=None, skiprows=5)
    s = pd.to_numeric(df.iloc[:, 3], errors='coerce').max() or 0
    l = pd.to_numeric(df.iloc[:, 4], errors='coerce').max() or 0
    stec = pd.to_numeric(df.iloc[:, 5], errors='coerce').max() or 0
    resa = pd.to_numeric(df.iloc[:, 6], errors='coerce').max() or 0
    total = s + l + stec + resa
    pct = s / total * 100 if total else 0
    print(f'{label:<12} {s:>12,.0f} {l:>12,.0f} {stec:>10,.0f} {resa:>10,.0f} {total:>12,.0f}  {pct:.1f}%')
    totals['Salmonella'] += s
    totals['Listeria'] += l
    totals['STEC'] += stec
    totals['RESA'] += resa

t = sum(totals.values())
print('-' * 60)
print(f'{"TOTAL":<12} {totals["Salmonella"]:>12,.0f} {totals["Listeria"]:>12,.0f} {totals["STEC"]:>10,.0f} {totals["RESA"]:>10,.0f} {t:>12,.0f}  {totals["Salmonella"]/t*100:.1f}%')
