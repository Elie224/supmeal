import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
import docx
d = docx.Document(r'C:\Users\KOURO\Downloads\Rapport_Projet_Fromagerie_v3_corrige.docx')
for i, p in enumerate(d.paragraphs):
    if i < 30:
        continue
    style = p.style.name if p.style else 'Normal'
    txt = p.text.strip()
    if txt:
        print(f'[{style[:14]:<14}] {txt[:220]}')
