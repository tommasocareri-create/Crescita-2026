import requests
import csv
import io

# L'ID estratto dal tuo link di Google Sheets
SHEET_ID = "1HlG6IDmzkwmpZ5LdfiQB5TM5Ma7y5tVzbwTC65u5K5k"
SHEET_NAME = "C.E."

MONTHS = [
    ("D","Gennaio"),("H","Febbraio"),("L","Marzo"),("P","Aprile"),
    ("T","Maggio"),("X","Giugno"),("AB","Luglio"),("AF","Agosto"),
    ("AJ","Settembre"),("AN","Ottobre"),("AR","Novembre"),("AV","Dicembre"),
]
MONTH_EXTRA = {
    "D":("E","F","G"),"H":("I","J","K"),"L":("M","N","O"),
    "P":("Q","R","S"),"T":("U","V","W"),"X":("Y","Z","AA"),
    "AB":("AC","AD","AE"),"AF":("AG","AH","AI"),"AJ":("AK","AL","AM"),
    "AN":("AO","AP","AQ"),"AR":("AS","AT","AU"),"AV":("AW","AX","AY"),
}
INCOME_ROWS    = {21:"Entrate Lorde Stipendio",22:"Altre Entrate",23:"Entrate Lorde",24:"Entrate Nette"}
PREV_YEAR_ROWS = {27:"Entrate Lorde Stipendio",28:"Altre Entrate",29:"Entrate Lorde",30:"Entrate Nette"}

def col_letter_to_index(col):
    result = 0
    for ch in col.upper():
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1

def _safe(v):
    if v is None or v == "": return None
    s = str(v)
    if any(x in s for x in ["DIV","REF","VALUE","N/A","#"]): return None
    clean = s.replace("€","").replace("$","").replace(" ","").replace("\xa0","").replace("−","-")
    if "." in clean and "," in clean:
        clean = clean.replace(".","").replace(",",".")
    elif "," in clean:
        clean = clean.replace(",",".")
    try:
        return float(clean)
    except:
        return None

def fetch_sheet_data():
    # 1. INCOLLA QUI TRA LE VIRGOLETTE IL LINK CHE HAI APPENA CREATO CON "PUBBLICA SUL WEB"
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJaIzdbR_Bs3r2nVZWPWglma3Vnd4Lp2m6yZYnBsJk3kQYBqcqS51yHBA1VapuXgjDk6j3kphwpsED/pub?gid=1658406014&single=true&output=csv"
    
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise Exception(f"Errore download Google Sheet ({resp.status_code}). Verifica il link.")
    
    # 2. CONTROLLO SALVAVITA: Stiamo ricevendo HTML invece di dati?
    if "<html" in resp.text.lower() or "<body" in resp.text.lower():
        raise Exception("Blocco di Google rilevato! Ricevuta una pagina HTML invece dei dati. Assicurati di aver generato il link da 'File > Condividi > Pubblica sul web'.")
        
    grid = {}
    for r_idx, row in enumerate(csv.reader(io.StringIO(resp.text))):
        for c_idx, val in enumerate(row):
            if val.strip():
                grid[(r_idx, c_idx)] = val.strip()
    return grid
def get_cell(grid, row_1indexed, col_letter):
    return grid.get((row_1indexed - 1, col_letter_to_index(col_letter)), None)

def load_data(path=None):
    grid = fetch_sheet_data()
    assets = []
    for row in range(9, 20):
        name  = get_cell(grid, row, "A")
        start = _safe(get_cell(grid, row, "B"))
        if name and isinstance(name, str) and name.strip():
            assets.append({"name": name.strip(), "start": start or 0})
    start_total = _safe(get_cell(grid, 8, "B")) or 0
    obj_total   = _safe(get_cell(grid, 8, "AZ"))
    objectives  = {a["name"]: _safe(get_cell(grid, 9+i, "AZ")) for i, a in enumerate(assets)}
    monthly_patrimonio = {}
    for col_letter, month_name in MONTHS:
        var_col, varpct_col, weight_col = MONTH_EXTRA[col_letter]
        total_val = _safe(get_cell(grid, 8, col_letter))
        filled    = total_val is not None and total_val > 0
        asset_data = [{"name": a["name"],
            "value":   _safe(get_cell(grid, 9+i, col_letter)),
            "var_eur": _safe(get_cell(grid, 9+i, var_col)),
            "var_pct": _safe(get_cell(grid, 9+i, varpct_col)),
            "weight":  _safe(get_cell(grid, 9+i, weight_col)),
        } for i, a in enumerate(assets)]
        monthly_patrimonio[month_name] = {"totale": total_val, "assets": asset_data, "filled": filled}
    monthly_income = {}
    for col_letter, month_name in MONTHS:
        stip  = _safe(get_cell(grid, 21, col_letter))
        altre = _safe(get_cell(grid, 22, col_letter))
        lorde = _safe(get_cell(grid, 23, col_letter))
        nette = _safe(get_cell(grid, 24, col_letter))
        if lorde is None and stip is not None and altre is not None:
            lorde = stip + altre
        monthly_income[month_name] = {
            "stipendio": stip, "altre": altre, "lorde": lorde, "nette": nette,
            "filled": any(x is not None for x in [stip, altre, lorde, nette]),
        }
    income_summary = {
        label: {"avg": _safe(get_cell(grid, row, "BB")),
                "total": _safe(get_cell(grid, row, "BC")),
                "yoy": _safe(get_cell(grid, row, "BD"))}
        for row, label in INCOME_ROWS.items()
    }
    prev_year = {label: _safe(get_cell(grid, row, "B")) for row, label in PREV_YEAR_ROWS.items()}
    cagr_ytd  = _safe(get_cell(grid, 20, "AZ"))
    return {
        "excel_path": SHEET_ID, "start_total": start_total,
        "assets": assets, "objectives": objectives, "obj_total": obj_total,
        "monthly_patrimonio": monthly_patrimonio, "monthly_income": monthly_income,
        "income_summary": income_summary, "prev_year": prev_year,
        "cagr_ytd": cagr_ytd, "months_order": [m for _, m in MONTHS],
    }

def get_filled_months(data):
    return [m for m in data["months_order"] if data["monthly_patrimonio"][m]["filled"]]
