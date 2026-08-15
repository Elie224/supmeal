import os, re
src = r"C:\Users\KOURO\Downloads\FICHES LOGISTIQUES\FICHES LOGISTIQUES"
for fname in sorted(os.listdir(src)):
    if "PETLU" in fname or "tarif" in fname:
        print(repr(fname))
        base = fname.rstrip(".xlsx")
        print("Base:", repr(base))
        m = re.match(r"^(\d{13})\s*-\s*(\d+)\s*(.+?)\s*tarif", base, re.IGNORECASE)
        print("Match:", m)
        print()
