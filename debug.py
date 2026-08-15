import re
f = "7622202377198 -   4326075 PETLU 140G SOFT MARBRE 7CA tarif 1,285 unit\xc3\xa9.xlsx"
base = f.rstrip(".xlsx")
print("Base:", repr(base))
# Pattern B: EAN13 - <sku> <desc> tarif ... unite
m = re.match(r"^(\d{13})\s*-\s*(\d+)\s*(.+?)\s*tarif.+unit\xc3\xa9$", base, re.IGNORECASE)
print("Match B:", m)
m = re.match(r"^(\d{13})\s*-\s*(\d+)\s*(.+?)\s*tarif", base, re.IGNORECASE)
print("Match B (no e accent):", m)
if m:
    print("Groups:", m.groups())
