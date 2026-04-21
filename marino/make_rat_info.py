"""Generate rat_information.xlsx from file_list.txt."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

FILE_LIST = Path(__file__).parent / "file_list.txt"
OUTPUT = Path(__file__).parent.parent / "src/pagan_lab_to_nwb/arc_behavior/rat_information.xlsx"

MUTATIONS = {
    "P221": "Nrxn1-m1",
    "P222": "Fmr1-m4",
    "P223": "Fmr1-m4",
    "P241": "Fmr1-m2",
    "P242": "Fmr1-m2",
    "P243": "Fmr1-m2",
    "P244": "Fmr1-m2",
    "P245": "Nrxn1-m1",
    "P246": "Nrxn1-m1",
    "P247": "Nrxn1-m1",
    "P248": "Nrxn1-m1",
    "P212": "Grin2b",
    "P213": "Grin2b",
    "P214": "Arid1b",
    "P215": "Arid1b",
    "P216": "Dyrk1a-m1",
    "P217": "Dyrk1a-m1",
    "P218": "Fmr1-m2",
    "P219": "Fmr1-m2",
    "P220": "Nrxn1-m1",
}

pattern = re.compile(r"data_@[^_]+_[^_]+_([^_]+)_(\d{6})[a-z]\.mat")

first_session: dict[str, datetime] = {}

with open(FILE_LIST) as f:
    for line in f:
        line = line.strip()
        fname = Path(line).name
        m = pattern.match(fname)
        if not m:
            continue
        rat, date_str = m.group(1), m.group(2)
        try:
            date = datetime.strptime(date_str, "%y%m%d")
        except ValueError:
            continue
        if rat not in first_session or date < first_session[rat]:
            first_session[rat] = date

rows = []
for rat, first_date in sorted(first_session.items()):
    dob = first_date - timedelta(weeks=7)
    mutation = MUTATIONS.get(rat, "")
    if mutation:
        genotype = f"Long Evans, {mutation} knockout"
    else:
        genotype = "Long Evans"
    rows.append({
        "Rat": rat,
        "Sex": "male",
        "Date of Birth": dob.date(),
        "Genotype": genotype,
    })

df = pd.DataFrame(rows)
df.to_excel(OUTPUT, index=False)
print(f"Written {len(df)} rats to {OUTPUT}")
