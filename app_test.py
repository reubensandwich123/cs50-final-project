import re
import pdfplumber

loc = "june-bank-statement.pdf"
with pdfplumber.open(loc) as pdf:
    page = pdf.pages[0]
    page2 = pdf.pages[1]
    text = page.extract_text()
    text2 = page2.extract_text()
    
#strip gets rid of whitespace
date = re.search((r"Account Summary\s+as\s(?:of|at)\s+(\d{1,2} [A-Z][a-z]{2} \d{4})"), text).group(1)
savings = re.search((r"SGD Equivalent\s([\S]*)"), text).group(1).strip()
name = re.search(r"(\(cid:\d+\))+\s*([\s\S]*?)\s*\(cid:\d+\)+", text).group(2).strip()

print(date)
name = name.splitlines()

for line in name:
    print(line)
print(savings)