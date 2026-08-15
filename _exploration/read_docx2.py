import docx
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

d = docx.Document(r'C:\Users\KOURO\Downloads\Rapport_Projet_Fromagerie_Phases_1_a_7.docx')
for i, p in enumerate(d.paragraphs):
    txt = p.text.strip()
    if txt and i > 50:
        print(f'[P{i}] {txt}')
