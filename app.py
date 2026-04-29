"""
app.py - Patrimonio 2026 Dashboard
Legge da Google Sheets (Piano 2026 - C.E.)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from reader import load_data, get_filled_months, SHEET_ID

st.set_page_config(page_title="Patrimonio 2026", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
    --navy:#0D1B2A; --navy2:#0A1520; --gold:#F0C040; --gold2:#FFD966;
    --teal:#00E5CC; --red:#FF5C5C; --cream:#FFFFFF; --muted:#B0C4D8;
    --card:#152233; --border:#1E3448; --green:#00E676;
}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:var(--navy)!important;color:var(--cream)!important;}
.stApp{background:var(--navy)!important;}
[data-testid="stSidebar"]{background:var(--navy2)!important;border-right:1px solid var(--border);}
[data-testid="stSidebar"] *{color:var(--cream)!important;}
.big-title{font-family:'DM Serif Display',serif;font-size:2.4rem;color:var(--gold);line-height:1.1;margin-bottom:0;}
.sub-title{font-family:'DM Mono',monospace;font-size:.7rem;color:var(--muted);letter-spacing:2.5px;text-transform:uppercase;margin-bottom:1.6rem;}
.sec-head{font-family:'DM Serif Display',serif;font-size:1.2rem;color:var(--gold2);border-bottom:2px solid var(--gold);padding-bottom:.3rem;margin:1.6rem 0 .9rem;}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.2rem 1.4rem;position:relative;overflow:hidden;}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--gold),var(--teal));}
.kpi-stip{background:linear-gradient(135deg,#1e3452,#0f2035);border:2px solid var(--gold);border-radius:14px;padding:1.2rem 1.4rem;position:relative;overflow:hidden;}
.kpi-stip::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--gold),#FF8C00);}
.kpi-lbl{font-family:'DM Mono',monospace;font-size:.62rem;color:var(--muted);letter-spacing:1.8px;text-transform:uppercase;margin-bottom:.4rem;}
.kpi-val{font-family:'DM Serif Display',serif;font-size:1.75rem;line-height:1;color:var(--cream);}
.kpi-sub{font-size:.78rem;margin-top:.3rem;}
.pos{color:#00E676!important;font-weight:600;}
.neg{color:#FF5C5C!important;font-weight:600;}
.neu{color:var(--muted);}
.teal{color:var(--teal)!important;font-weight:600;}
.prog-wrap{background:var(--border);border-radius:4px;height:7px;margin-top:7px;}
.prog-bar{height:7px;border-radius:4px;}
.pill{display:inline-block;padding:.18rem .7rem;border-radius:20px;font-family:'DM Mono',monospace;font-size:.68rem;margin:2px;}
.pill-ok{background:rgba(0,229,204,.15);color:#00E5CC;border:1px solid #00E5CC;}
.pill-no{background:rgba(168,187,206,.08);color:var(--muted);border:1px solid var(--border);}
div[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;}
.stButton>button{background:linear-gradient(135deg,var(--gold),#B8860B)!important;color:#0D1B2A!important;font-weight:700!important;border:none!important;border-radius:8px!important;}
</style>
""", unsafe_allow_html=True)

PALETTE = ["#F0C040","#00E5CC","#FF6B6B","#5BA4CF","#A8DADC","#FFD966","#00BCD4","#FF8A65","#CE93D8","#EF9A9A","#80DEEA"]
EUR_USD = 1.085

def fe(v, mul=1, sym="€", sign=False):
    if v is None: return "—"
    v2 = v * mul
    prefix = "+" if (sign and v2 > 0) else ""
    return f"{prefix}{sym}{v2:,.0f}".replace(",", ".")

def fp(v, decimals=2):
    if v is None: return "—"
    prefix = "+" if v > 0 else ""
    return f"{prefix}{v*100:.{decimals}f}%"

def dc(v):
    if v is None or v == 0: return "neu"
    return "pos" if v > 0 else "neg"

def kpi(label, value, sub="", sub_class="neu", gold=False):
    val_col = "#F0C040" if gold else "#FFFFFF"
    return f"""<div class="kpi">
  <div class="kpi-lbl">{label}</div>
  <div class="kpi-val" style="color:{val_col}">{value}</div>
  <div class="kpi-sub {sub_class}">{sub}</div>
</div>"""

def kpi_stip(label, value, sub="", sub_color="#F0C040"):
    return f"""<div class="kpi-stip">
  <div class="kpi-lbl">{label}</div>
  <div class="kpi-val" style="color:#FFD966">{value}</div>
  <div class="kpi-sub" style="color:{sub_color}">{sub}</div>
</div>"""

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", family="DM Sans"),
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis=dict(gridcolor="#1E3448", color="#FFFFFF"),
    yaxis=dict(gridcolor="#1E3448", color="#FFFFFF"),
)

def color_var(val):
    try:
        if val > 0: return "color:#00E676;font-weight:600"
        if val < 0: return "color:#FF5C5C;font-weight:600"
    except: pass
    return "color:#B0C4D8"

def color_prog(val):
    try:
        if val >= 100: return "color:#00E676;font-weight:600"
        if val >= 70:  return "color:#F0C040;font-weight:600"
        return "color:#FF5C5C;font-weight:600"
    except: pass
    return ""

TABLE_PROPS = {"background-color":"#152233","color":"#FFFFFF","border":"1px solid #1E3448","font-size":"13px","padding":"8px 12px"}
TABLE_TH = [{"selector":"th","props":[("background-color","#0A1520"),("color","#F0C040"),("font-size","11px"),("text-transform","uppercase"),("padding","8px 12px"),("border","1px solid #1E3448")]}]

@st.cache_data(ttl=30)
def get_data():
    return load_data()

with st.sidebar:
    st.markdown('<div style="font-family:DM Serif Display,serif;font-size:1.5rem;color:#F0C040">💰 Patrimonio</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:DM Mono,monospace;font-size:.65rem;color:#B0C4D8;letter-spacing:2px;margin-bottom:.5rem">2026 TRACKER</div>', unsafe_allow_html=True)
    cur_choice = st.radio("Valuta", ["€ EUR", "$ USD"], horizontal=True)
    cur = "USD" if "USD" in cur_choice else "EUR"
    sym = "$" if cur == "USD" else "€"
    mul = EUR_USD if cur == "USD" else 1.0
    if cur == "USD":
        st.markdown(f'<div style="font-size:.68rem;color:#F0C040;font-family:DM Mono,monospace">1 € = {EUR_USD} $</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("", ["📊 Dashboard", "📋 Tabella Mensile", "📈 Grafici", "💸 Entrate"], label_visibility="collapsed")
    st.divider()
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
   st.markdown('<div style="font-family:DM Mono,monospace;font-size:.62rem;color:#B0C4D8;letter-spacing:1.5px;margin-top:.6rem">MESI COMPILATI</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.63rem;color:#B0C4D8;margin-top:.5rem;font-family:DM Mono,monospace">📊 Google Sheets · Live</div>', unsafe_allow_html=True)

try:
    data = get_data()
    filled = get_filled_months(data)
except Exception as e:
    st.error(f"Errore lettura Google Sheet: {e}")
    st.stop()

with st.sidebar:
    if filled:
        pills = "".join(f'<span class="pill {"pill-ok" if m in filled else "pill-no"}">{m[:3].upper()}</span>' for m in data["months_order"])
        st.markdown(pills, unsafe_allow_html=True)

months_order = data["months_order"]
assets       = data["assets"]
objectives   = data["objectives"]
obj_total    = data["obj_total"] or 0
start_total  = data["start_total"]
mp           = data["monthly_patrimonio"]
mi           = data["monthly_income"]
inc_summary  = data["income_summary"]
prev_year    = data["prev_year"]
last_month   = filled[-1] if filled else None
last_total   = mp[last_month]["totale"] if last_month else start_total
prev_month   = filled[-2] if len(filled) >= 2 else None
delta_ytd    = last_total - start_total if last_month else 0
pct_ytd      = delta_ytd / start_total if start_total else 0
delta_mom    = (last_total - (mp[prev_month]["totale"] or 0)) if prev_month and last_month else 0
pct_mom      = delta_mom / mp[prev_month]["totale"] if prev_month and mp[prev_month]["totale"] else 0
cagr_ytd     = data["cagr_ytd"] or 0
months_done  = len(filled)
prog_obj     = (last_total / obj_total * 100) if obj_total else 0
if page == "📊 Dashboard":
    st.markdown('<div class="big-title">Patrimonio 2026</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">Aggiornato al {last_month or "—"} · {sym} {cur}</div>', unsafe_allow_html=True)
    if not filled:
        st.warning("Nessun mese compilato nel Google Sheet.")
    k1, k2, k3, k4 = st.columns(4)
    bar = min(prog_obj, 100)
    with k1:
        st.markdown(
            kpi(f"Patrimonio Attuale {sym}", fe(last_total, mul, sym),
                f"{fe(delta_ytd, mul, sym, sign=True)} ({fp(pct_ytd)}) da dic 2025", dc(delta_ytd))
            + f'<div class="prog-wrap"><div class="prog-bar" style="width:{bar:.1f}%;background:linear-gradient(90deg,#F0C040,#00E5CC)"></div></div>'
            + f'<div style="font-size:.63rem;color:#B0C4D8;margin-top:4px;font-family:DM Mono,monospace">{bar:.1f}% dell\'obiettivo</div>',
            unsafe_allow_html=True)
    with k2:
        gap = last_total - obj_total
        gap_txt = "✓ Obiettivo raggiunto!" if gap >= 0 else f"{fe(gap, mul, sym, sign=True)} al traguardo"
        st.markdown(kpi(f"Obiettivo Annuale {sym}", fe(obj_total, mul, sym), gap_txt, "pos" if gap >= 0 else "neg", gold=True), unsafe_allow_html=True)
    with k3:
        lbl = f"{last_month} vs {prev_month}" if prev_month else (last_month or "—")
        st.markdown(kpi("Variazione Mensile", fp(pct_mom) if last_month else "—",
            f"{fe(delta_mom, mul, sym, sign=True)} · {lbl}", dc(delta_mom)), unsafe_allow_html=True)
    with k4:
        ann = ((1 + cagr_ytd) ** (12 / months_done) - 1) if months_done > 0 and cagr_ytd != 0 else 0
        st.markdown(kpi("CAGR Annualizzato", fp(ann),
            f"YTD: {fp(cagr_ytd)} · {months_done} mes{'e' if months_done==1 else 'i'}", dc(ann)), unsafe_allow_html=True)
    st.markdown('<div class="sec-head">Andamento Patrimonio vs Forecast</div>', unsafe_allow_html=True)
    if filled:
        x = [m[:3].upper() for m in filled]
        totals_g = [(mp[m]["totale"] or 0)*mul for m in filled]
        fc_g = [(start_total + (obj_total-start_total)/12*(i+1))*mul for i in range(len(filled))]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=totals_g, name="Patrimonio",
            mode="lines+markers", line=dict(color="#F0C040", width=2.5), marker=dict(size=8, color="#F0C040"),
            fill="tozeroy", fillcolor="rgba(240,192,64,0.08)",
            hovertemplate=f"%{{x}}: {sym}%{{y:,.0f}}<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=fc_g, name="Forecast",
            mode="lines", line=dict(color="#00E5CC", width=1.8, dash="dash")))
        fig.add_hline(y=start_total*mul, line_dash="dot", line_color="#B0C4D8",
            annotation_text=f"Start {sym}{start_total*mul:,.0f}".replace(",","."), annotation_font_color="#B0C4D8", annotation_position="bottom right")
        fig.add_hline(y=obj_total*mul, line_dash="dot", line_color="#F0C040",
            annotation_text=f"Obiettivo {sym}{obj_total*mul:,.0f}".replace(",","."), annotation_font_color="#F0C040", annotation_position="top right")
        fig.update_layout(height=340, legend=dict(orientation="h", y=-0.18, font_color="#FFFFFF"),
            xaxis=dict(gridcolor="#1E3448", color="#FFFFFF"),
            yaxis=dict(gridcolor="#1E3448", tickformat=",.0f", tickprefix=sym, color="#FFFFFF"),
            **{k: v for k, v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis"]})
        st.plotly_chart(fig, use_container_width=True)
    if last_month:
        st.markdown('<div class="sec-head">Asset Allocation · Ultimo Mese</div>', unsafe_allow_html=True)
        col_pie, col_tab = st.columns([1, 1.1])
        asset_data = mp[last_month]["assets"]
        total_m = (mp[last_month]["totale"] or 1) * mul
        pie_labels = [a["name"] for a in asset_data if (a["value"] or 0) > 0]
        pie_vals   = [(a["value"] or 0)*mul for a in asset_data if (a["value"] or 0) > 0]
        with col_pie:
            fig_pie = go.Figure(go.Pie(labels=pie_labels, values=pie_vals, hole=0.44,
                marker=dict(colors=PALETTE[:len(pie_labels)], line=dict(color="#0D1B2A", width=2)),
                textinfo="label+percent", textfont=dict(size=11, color="#FFFFFF"),
                hovertemplate=f"<b>%{{label}}</b><br>{sym}%{{value:,.0f}}<br>%{{percent}}<extra></extra>"))
            fig_pie.update_layout(height=360, showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#FFFFFF"), margin=dict(l=0,r=0,t=10,b=0),
                annotations=[dict(text=f"{sym}{total_m:,.0f}".replace(",","."),
                    x=0.5, y=0.5, showarrow=False, font=dict(size=13, color="#F0C040", family="DM Serif Display"))])
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_tab:
            rows = []
            for a in asset_data:
                v   = (a["value"] or 0) * mul
                var = (a["var_eur"] or 0) * mul if a["var_eur"] is not None else None
                vp  = a["var_pct"]
                obj_v = objectives.get(a["name"])
                obj = obj_v * mul if obj_v else None
                rows.append({"Voce": a["name"], "Valore": v, "Var": var,
                    "Var %": (vp*100) if vp is not None else None,
                    "Peso %": (v/total_m*100),
                    "Obiettivo": obj, "Prog %": (v/obj*100) if obj else None})
            df = pd.DataFrame(rows)
            styled = (df.style
                .format({"Valore": lambda x: f"{sym}{x:,.0f}" if pd.notna(x) else "—",
                         "Var": lambda x: f"{'+' if x>0 else ''}{sym}{x:,.0f}" if pd.notna(x) else "—",
                         "Var %": lambda x: f"{x:+.2f}%" if pd.notna(x) else "—",
                         "Peso %": "{:.2f}%",
                         "Obiettivo": lambda x: f"{sym}{x:,.0f}" if pd.notna(x) else "—",
                         "Prog %": lambda x: f"{x:.1f}%" if pd.notna(x) else "—"})
                .map(color_var, subset=["Var","Var %"])
                .map(color_prog, subset=["Prog %"])
                .set_properties(**TABLE_PROPS)
                .set_table_styles(TABLE_TH))
            st.dataframe(styled, use_container_width=True, hide_index=True, height=340)

elif page == "📋 Tabella Mensile":
    st.markdown('<div class="big-title">Tabella Mensile</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">Dettaglio patrimonio mese per mese · {sym} {cur}</div>', unsafe_allow_html=True)
    if not filled:
        st.warning("Nessun dato disponibile.")
        st.stop()
    sel_month = st.selectbox("Seleziona mese", filled, index=len(filled)-1)
    m_data  = mp[sel_month]
    total_m = (m_data["totale"] or 1) * mul
    prev_m  = filled[filled.index(sel_month)-1] if filled.index(sel_month) > 0 else None
    prev_t  = (mp[prev_m]["totale"] if prev_m else start_total) * mul
    var_tot = total_m - prev_t
    pct_tot = var_tot / prev_t if prev_t else 0
    rows = [{"Voce":"▸ TOTALE PATRIMONIO", "Valore":total_m, "Var":var_tot,
             "Var %":pct_tot*100, "Peso %":100.0, "Obiettivo":obj_total*mul,
             "Prog %":(total_m/(obj_total*mul)*100) if obj_total else None}]
    for a in m_data["assets"]:
        v   = (a["value"] or 0)*mul
        var = (a["var_eur"] or 0)*mul if a["var_eur"] is not None else None
        obj_v = objectives.get(a["name"])
        obj = obj_v*mul if obj_v else None
        rows.append({"Voce":a["name"], "Valore":v, "Var":var,
            "Var %":(a["var_pct"]*100) if a["var_pct"] is not None else None,
            "Peso %":(v/total_m*100), "Obiettivo":obj, "Prog %":(v/obj*100) if obj else None})
    df = pd.DataFrame(rows)
    fmt_v = lambda x: f"{sym}{x:,.0f}" if pd.notna(x) else "—"
    fmt_var = lambda x: f"{'+' if x>0 else ''}{sym}{x:,.0f}" if pd.notna(x) else "—"
    styled = (df.style
        .format({"Valore":fmt_v,"Var":fmt_var,
                 "Var %":lambda x:f"{x:+.2f}%" if pd.notna(x) else "—",
                 "Peso %":"{:.2f}%","Obiettivo":fmt_v,
                 "Prog %":lambda x:f"{x:.1f}%" if pd.notna(x) else "—"})
        .map(color_var, subset=["Var","Var %"])
        .map(color_prog, subset=["Prog %"])
        .set_properties(**TABLE_PROPS)
        .set_table_styles(TABLE_TH + [{"selector":"tr:first-child td","props":[("background-color","rgba(240,192,64,0.12)"),("font-weight","bold"),("color","#FFD966")]}]))
    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.markdown('<div class="sec-head">Riepilogo Tutti i Mesi</div>', unsafe_allow_html=True)
    sum_rows = []
    for m in filled:
        t  = (mp[m]["totale"] or 0)*mul
        pv = (mp[filled[filled.index(m)-1]]["totale"] if filled.index(m)>0 else start_total)*mul
        va = t - pv
        pc = va/pv if pv else 0
        sum_rows.append({"Mese":m,"Totale":t,"Var":va,"Var %":pc*100,"vs Obiettivo %":(t/(obj_total*mul)*100) if obj_total else None})
    df_s = pd.DataFrame(sum_rows)
    st_s = (df_s.style
        .format({"Totale":fmt_v,"Var":fmt_var,
                 "Var %":lambda x:f"{x:+.2f}%" if pd.notna(x) else "—",
                 "vs Obiettivo %":lambda x:f"{x:.1f}%" if pd.notna(x) else "—"})
        .map(color_var, subset=["Var","Var %"])
        .background_gradient(subset=["Totale"], cmap="YlOrBr")
        .set_properties(**TABLE_PROPS)
        .set_table_styles(TABLE_TH))
    st.dataframe(st_s, use_container_width=True, hide_index=True)
elif page == "📈 Grafici":
    st.markdown('<div class="big-title">Grafici</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">Analisi visuale · Patrimonio & Voci · {sym} {cur}</div>', unsafe_allow_html=True)
    if not filled:
        st.warning("Nessun dato disponibile.")
        st.stop()
    x_short = [m[:3].upper() for m in filled]
    st.markdown('<div class="sec-head">Andamento Cumulato Patrimonio</div>', unsafe_allow_html=True)
    totals_g = [(mp[m]["totale"] or 0)*mul for m in filled]
    fc_g     = [(start_total+(obj_total-start_total)/12*(i+1))*mul for i in range(len(filled))]
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=x_short, y=totals_g, name="Patrimonio",
        mode="lines+markers", line=dict(color="#F0C040",width=2.5), marker=dict(size=8,color="#F0C040"),
        fill="tozeroy", fillcolor="rgba(240,192,64,0.08)",
        hovertemplate=f"%{{x}}: {sym}%{{y:,.0f}}<extra></extra>"))
    fig1.add_trace(go.Scatter(x=x_short, y=fc_g, name="Forecast",
        mode="lines", line=dict(color="#00E5CC",width=1.8,dash="dash")))
    fig1.add_hline(y=start_total*mul, line_dash="dot", line_color="#B0C4D8",
        annotation_text=f"Start {sym}{start_total*mul:,.0f}".replace(",","."), annotation_font_color="#B0C4D8")
    fig1.add_hline(y=obj_total*mul, line_dash="dot", line_color="#F0C040",
        annotation_text=f"Obiettivo {sym}{obj_total*mul:,.0f}".replace(",","."), annotation_font_color="#F0C040")
    fig1.update_layout(height=360, legend=dict(orientation="h",y=-0.15,font_color="#FFFFFF"),
        xaxis=dict(gridcolor="#1E3448",color="#FFFFFF"),
        yaxis=dict(gridcolor="#1E3448",tickformat=",.0f",tickprefix=sym,color="#FFFFFF"),
        **{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis"]})
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown('<div class="sec-head">Andamento Singole Voci</div>', unsafe_allow_html=True)
    ca, cb = st.columns([2,1])
    with ca:
        sel_assets = st.multiselect("Voci", [a["name"] for a in assets], default=[a["name"] for a in assets], key="gsel")
    with cb:
        view = st.radio("Vista", ["Valore", "Var % mensile", "Var % YTD"], key="gview")
    fig2 = go.Figure()
    for i, a in enumerate(assets):
        if a["name"] not in sel_assets: continue
        y_data = []
        for m in filled:
            ad = next((x for x in mp[m]["assets"] if x["name"]==a["name"]), None)
            if ad is None: y_data.append(None); continue
            if view == "Valore":
                y_data.append((ad["value"] or 0)*mul)
            elif view == "Var % mensile":
                y_data.append((ad["var_pct"]*100) if ad["var_pct"] is not None else None)
            else:
                sv = a["start"] or 1
                v  = ad["value"]
                y_data.append(((v-sv)/sv*100) if v is not None else None)
        fig2.add_trace(go.Scatter(x=x_short, y=y_data, name=a["name"],
            mode="lines+markers", line=dict(color=PALETTE[i%len(PALETTE)],width=2.2),
            marker=dict(size=6), connectgaps=False))
    yax = dict(gridcolor="#1E3448",tickprefix=sym,tickformat=",.0f",color="#FFFFFF") \
        if view=="Valore" else dict(gridcolor="#1E3448",ticksuffix="%",tickformat=".1f",color="#FFFFFF")
    fig2.update_layout(height=420, legend=dict(orientation="h",y=-0.22,font_size=11,font_color="#FFFFFF"),
        xaxis=dict(gridcolor="#1E3448",color="#FFFFFF"), yaxis=yax,
        **{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis"]})
    if view != "Valore": fig2.add_hline(y=0, line_color="#B0C4D8", line_width=1)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('<div class="sec-head">Heatmap Variazioni % Mensili</div>', unsafe_allow_html=True)
    hm_z, hm_y = [], []
    for a in assets:
        row = []
        for m in filled:
            ad = next((x for x in mp[m]["assets"] if x["name"]==a["name"]), None)
            vp = (ad["var_pct"]*100) if (ad and ad["var_pct"] is not None) else None
            row.append(round(vp,2) if vp is not None else None)
        hm_z.append(row); hm_y.append(a["name"])
    fig_hm = go.Figure(go.Heatmap(z=hm_z, x=x_short, y=hm_y,
        colorscale=[[0,"#FF5C5C"],[0.5,"#152233"],[1,"#00E5CC"]], zmid=0,
        text=[[f"{v:+.1f}%" if v is not None else "" for v in row] for row in hm_z],
        texttemplate="%{text}", textfont=dict(size=11,family="DM Mono",color="#FFFFFF"),
        hovertemplate="%{y}<br>%{x}: %{z:+.2f}%<extra></extra>",
        colorbar=dict(ticksuffix="%",tickfont=dict(color="#FFFFFF"))))
    fig_hm.update_layout(height=max(300,len(assets)*30),
        xaxis=dict(color="#FFFFFF"), yaxis=dict(tickfont=dict(size=11,color="#FFFFFF")),
        **{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis"]})
    st.plotly_chart(fig_hm, use_container_width=True)
    st.markdown('<div class="sec-head">Composizione per Mese</div>', unsafe_allow_html=True)
    pie_month = st.select_slider("Mese", options=filled, value=filled[-1], key="pie_sl") if len(filled)>1 else filled[0]
    pie_data  = mp[pie_month]["assets"]
    pie_labels = [a["name"] for a in pie_data if (a["value"] or 0) > 0]
    pie_vals   = [(a["value"] or 0)*mul for a in pie_data if (a["value"] or 0) > 0]
    total_pie  = (mp[pie_month]["totale"] or 0)*mul
    fig_pie = go.Figure(go.Pie(labels=pie_labels, values=pie_vals, hole=0.44,
        marker=dict(colors=PALETTE[:len(pie_labels)], line=dict(color="#0D1B2A",width=2)),
        textinfo="label+percent", textfont=dict(size=11,color="#FFFFFF"),
        hovertemplate=f"<b>%{{label}}</b><br>{sym}%{{value:,.0f}}<br>%{{percent}}<extra></extra>"))
    fig_pie.update_layout(height=420, showlegend=True,
        legend=dict(orientation="v",x=1,font_size=11,font_color="#FFFFFF"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF"), margin=dict(l=0,r=10,t=10,b=0),
        annotations=[dict(text=f"{sym}{total_pie:,.0f}".replace(",","."),
            x=0.37, y=0.5, showarrow=False, font=dict(size=14,color="#F0C040",family="DM Serif Display"))])
    st.plotly_chart(fig_pie, use_container_width=True)
elif page == "💸 Entrate":
    st.markdown('<div class="big-title">Entrate 2026</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">Stipendio · Altre Entrate · Netto · {sym} {cur}</div>', unsafe_allow_html=True)
    filled_inc = [m for m in months_order if mi[m]["filled"]]
    stip_ytd  = sum((mi[m]["stipendio"] or 0) for m in filled_inc) * mul
    stip_avg  = stip_ytd / len(filled_inc) if filled_inc else 0
    lorde_ytd = (inc_summary.get("Entrate Lorde",{}).get("total") or 0) * mul
    nette_ytd = (inc_summary.get("Entrate Nette",{}).get("total") or 0) * mul
    lorde_avg = (inc_summary.get("Entrate Lorde",{}).get("avg") or 0) * mul
    nette_avg = (inc_summary.get("Entrate Nette",{}).get("avg") or 0) * mul
    aliquota  = (1 - nette_ytd/lorde_ytd)*100 if lorde_ytd else 0
    yoy_lorde = inc_summary.get("Entrate Lorde",{}).get("yoy")
    py_stip_m  = (prev_year.get("Entrate Lorde Stipendio") or 0)*mul
    py_lorde_m = (prev_year.get("Entrate Lorde") or 0)*mul
    py_nette_m = (prev_year.get("Entrate Nette") or 0)*mul
    st.markdown('<div class="sec-head">📅 Anno Corrente 2026</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(kpi_stip("⭐ Entrate Lorde Stipendio YTD",
            f"{sym}{stip_ytd:,.0f}".replace(",","."),
            f"Media mensile: {sym}{stip_avg:,.0f}".replace(",",".")), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("Lorde Totali YTD", f"{sym}{lorde_ytd:,.0f}".replace(",","."),
            f"Media: {sym}{lorde_avg:,.0f}/mese".replace(",",".")), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi("Nette YTD", f"{sym}{nette_ytd:,.0f}".replace(",","."),
            f"Media: {sym}{nette_avg:,.0f}/mese".replace(",","."), "teal"), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi("Aliquota Effettiva", f"{aliquota:.1f}%", "Pressione fiscale YTD"), unsafe_allow_html=True)
    with k5:
        css_yoy = "pos" if (yoy_lorde or 0) >= 0 else "neg"
        st.markdown(kpi("YoY Entrate Lorde", fp(yoy_lorde) if yoy_lorde is not None else "—",
            "vs anno precedente", css_yoy), unsafe_allow_html=True)
    st.markdown('<div class="sec-head">📆 Riferimento Anno Precedente 2025</div>', unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(kpi_stip("⭐ Stip. Lordo/mese 2025",
            f"{sym}{py_stip_m:,.0f}".replace(",","."),
            f"Totale anno: {sym}{py_stip_m*12:,.0f}".replace(",",".")), unsafe_allow_html=True)
    with p2:
        st.markdown(kpi("Lorde/mese 2025", f"{sym}{py_lorde_m:,.0f}".replace(",","."),
            f"Totale: {sym}{py_lorde_m*12:,.0f}".replace(",",".")), unsafe_allow_html=True)
    with p3:
        st.markdown(kpi("Nette/mese 2025", f"{sym}{py_nette_m:,.0f}".replace(",","."),
            f"Totale: {sym}{py_nette_m*12:,.0f}".replace(",","."), "teal"), unsafe_allow_html=True)
    with p4:
        py_al = (1 - py_nette_m/py_lorde_m)*100 if py_lorde_m else 0
        st.markdown(kpi("Aliquota 2025", f"{py_al:.1f}%", "Pressione fiscale media"), unsafe_allow_html=True)
    if not filled_inc:
        st.warning("Nessun dato entrate nel Google Sheet.")
        st.stop()
    st.markdown('<div class="sec-head">Entrate Mensili & Cumulate</div>', unsafe_allow_html=True)
    x_inc   = [m[:3].upper() for m in filled_inc]
    lorde_m = [(mi[m]["lorde"] or 0)*mul for m in filled_inc]
    nette_m = [(mi[m]["nette"] or 0)*mul for m in filled_inc]
    stip_m  = [(mi[m]["stipendio"] or 0)*mul for m in filled_inc]
    altre_m = [(mi[m]["altre"] or 0)*mul for m in filled_inc]
    lorde_cum = list(np.cumsum(lorde_m))
    nette_cum = list(np.cumsum(nette_m))
    n = len(filled_inc)
    py_lc = [py_lorde_m*i for i in range(1,n+1)]
    py_nc = [py_nette_m*i for i in range(1,n+1)]
    fig_inc = make_subplots(rows=2, cols=1,
        subplot_titles=["Mensile", "Cumulato (tratteggiato = riferimento 2025)"],
        vertical_spacing=0.15)
    fig_inc.add_trace(go.Bar(x=x_inc, y=stip_m,  name="Stipendio lordo", marker_color="#5BA4CF", opacity=0.9), row=1, col=1)
    fig_inc.add_trace(go.Bar(x=x_inc, y=altre_m, name="Altre entrate",   marker_color="#00E5CC", opacity=0.9), row=1, col=1)
    fig_inc.add_trace(go.Scatter(x=x_inc, y=nette_m, name="Nette",
        mode="lines+markers", line=dict(color="#F0C040",width=2.5), marker=dict(size=8)), row=1, col=1)
    fig_inc.add_trace(go.Scatter(x=x_inc, y=lorde_cum, name="Lorde cum.",
        mode="lines+markers", line=dict(color="#00E5CC",width=2.5), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(0,229,204,0.08)"), row=2, col=1)
    fig_inc.add_trace(go.Scatter(x=x_inc, y=nette_cum, name="Nette cum.",
        mode="lines+markers", line=dict(color="#F0C040",width=2.5), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(240,192,64,0.07)"), row=2, col=1)
    fig_inc.add_trace(go.Scatter(x=x_inc, y=py_lc, name="Lorde 2025",
        mode="lines", line=dict(color="#00E5CC",width=1.2,dash="dot"), opacity=0.5), row=2, col=1)
    fig_inc.add_trace(go.Scatter(x=x_inc, y=py_nc, name="Nette 2025",
        mode="lines", line=dict(color="#F0C040",width=1.2,dash="dot"), opacity=0.5), row=2, col=1)
    fig_inc.update_layout(height=600, barmode="stack",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF",family="DM Sans"),
        legend=dict(orientation="h",y=-0.07,font_size=11,font_color="#FFFFFF"),
        margin=dict(l=10,r=10,t=40,b=10))
    for ax in ["xaxis","xaxis2"]:
        fig_inc.update_layout(**{ax: dict(gridcolor="#1E3448",color="#FFFFFF")})
    for ax in ["yaxis","yaxis2"]:
        fig_inc.update_layout(**{ax: dict(gridcolor="#1E3448",tickformat=",.0f",tickprefix=sym,color="#FFFFFF")})
    st.plotly_chart(fig_inc, use_container_width=True)
    st.markdown('<div class="sec-head">Riepilogo per Mese</div>', unsafe_allow_html=True)
    fmt_v = lambda x: f"{sym}{x:,.0f}" if pd.notna(x) else "—"
    inc_rows = []
    for m in filled_inc:
        inc_rows.append({"Mese":m,
            "Stip. Lordo":   (mi[m]["stipendio"] or 0)*mul,
            "Altre Entrate": (mi[m]["altre"] or 0)*mul,
            "Lorde Totali":  (mi[m]["lorde"] or 0)*mul,
            "Nette":         (mi[m]["nette"] or 0)*mul,
            "Aliquota %":    ((1-(mi[m]["nette"] or 0)/(mi[m]["lorde"] or 1))*100) if mi[m]["lorde"] else None})
    df_inc = pd.DataFrame(inc_rows)
    styled_inc = (df_inc.style
        .format({"Stip. Lordo":fmt_v,"Altre Entrate":fmt_v,"Lorde Totali":fmt_v,"Nette":fmt_v,
                 "Aliquota %":lambda x:f"{x:.1f}%" if pd.notna(x) else "—"})
        .set_properties(**TABLE_PROPS)
        .set_table_styles(TABLE_TH))
    st.dataframe(styled_inc, use_container_width=True, hide_index=True)
