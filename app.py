# app.py
# "Suderduper random gruppe" – Presentasjonsmodus (uten input), to kolonner, boksvisning

import math
import random
import colorsys
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Suderduper random gruppe", page_icon="🎲", layout="wide")

# ---------- CSS: bakgrunn, tittel, typografi, tynn HR, boks ----------
st.markdown("""
<style>
/* Multifarget bakgrunn */
.stApp {
  background:
    radial-gradient(1100px 700px at 8% 10%, #ffe9f0, transparent 60%),
    radial-gradient(1100px 700px at 92% 18%, #e9f7ff, transparent 60%),
    radial-gradient(1100px 700px at 18% 88%, #eefbe8, transparent 60%),
    radial-gradient(1100px 700px at 82% 84%, #fff7e6, transparent 60%),
    linear-gradient(135deg, #eef3ff 0%, #ffffff 50%, #fff0f6 100%);
}

/* App-tittel i gradient */
.app-title {
  font-weight: 900;
  font-size: clamp(30px, 6vw, 64px);
  line-height: 1.05;
  letter-spacing: 0.3px;
  background: linear-gradient(90deg, #7b2ff7, #f107a3, #ff6b6b, #feca57, #1dd1a1, #54a0ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin: 8px 0 2px 0;
}

/* Gruppe-overskrifter */
h1.grp {
  font-size: clamp(24px, 3.0vw, 40px);   /* størst */
  margin: 0.2rem 0 0.25rem 0;
  font-weight: 900;
}
h2.grp {
  font-size: clamp(18px, 2.2vw, 28px);   /* mellom */
  margin: 0.15rem 0 0.2rem 0;
  font-weight: 750;
}
h3.grp {
  font-size: clamp(14px, 1.7vw, 22px);   /* minst */
  margin: 0.1rem 0 0.15rem 0;
  font-weight: 700;
  font-style: italic;                     /* kursiv */
  opacity: 0.9;
}

/* Tynn separator */
hr {
  border: none;
  border-top: 0.5px solid rgba(0,0,0,0.18);
  margin: 0.6rem 0 0.8rem 0;
}

/* Boksvisning (kort) – ren og diskré */
.group-card {
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 14px;
  background: rgba(255,255,255,0.72);
  padding: 12px 14px;
  margin-bottom: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* Inputs lesbarhet */
textarea, .stTextInput input {
  background: rgba(255,255,255,0.92) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
if "groups" not in st.session_state:
    st.session_state["groups"] = None
if "group_colors" not in st.session_state:
    st.session_state["group_colors"] = None
if "present" not in st.session_state:
    st.session_state["present"] = False

# ---------- Hjelpefunksjoner ----------
def parse_names(text: str):
    if not text:
        return []
    raw = []
    for chunk in text.replace(";", "\n").replace(",", "\n").split("\n"):
        name = chunk.strip()
        if name:
            raw.append(name)
    # fjern dubletter, bevar rekkefølge (case-insensitive)
    seen = set()
    out = []
    for n in raw:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out

def planned_group_sizes(n_students: int, n_groups: int):
    base = n_students // n_groups
    rem = n_students % n_groups
    return [base + (1 if i < rem else 0) for i in range(n_groups)]

def distribute_with_separation(all_names, separated_names, targets, rng: random.Random):
    n_groups = len(targets)
    if len(separated_names) > n_groups:
        raise ValueError(
            "Det er flere i «må være i ulike grupper»-feltet enn antall grupper. "
            "Reduser antall per gruppe (gir flere grupper) eller fjern noen fra listen."
        )
    groups = [[] for _ in range(n_groups)]

    # Plasser separasjons-elever først (rundgang til gruppe med plass)
    for i, name in enumerate(separated_names):
        start = i % n_groups
        placed = False
        for off in range(n_groups):
            g = (start + off) % n_groups
            if len(groups[g]) < targets[g]:
                groups[g].append(name)
                placed = True
                break
        if not placed:
            raise ValueError("Fant ikke plass til en separasjons-elev innenfor ønskede gruppestørrelser.")

    # Resten tilfeldig, prioriter gruppa med mest relativ plass
    remaining = [n for n in all_names if n not in separated_names]
    rng.shuffle(remaining)
    for name in remaining:
        order = sorted(range(n_groups), key=lambda g: (len(groups[g]) / targets[g], len(groups[g])))
        for g in order:
            if len(groups[g]) < targets[g]:
                groups[g].append(name)
                break
    return groups

def groups_to_dataframe(groups):
    rows = []
    for i, grp in enumerate(groups, 1):
        for m in grp:
            rows.append({"Gruppe": i, "Navn": m})
    return pd.DataFrame(rows)

def hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

def make_random_group_colors(n, rng: random.Random):
    """Lag pene, jevnt fordelte farger; stokkes for variasjon."""
    if n <= 0:
        return []
    hues = [i / n for i in range(n)]
    rng.shuffle(hues)
    colors = []
    for h in hues:
        s = 0.70
        l = 0.45
        colors.append(hsl_to_hex(h, s, l))
    return colors

def render_groups(groups, colors):
    """Tegner grupper i to kolonner med boksvisning."""
    for row in range(0, len(groups), 2):
        col_left, col_right = st.columns(2)
        for j, col in enumerate((col_left, col_right)):
            idx = row + j
            if idx < len(groups):
                grp = groups[idx]
                color = colors[idx % len(colors)]
                names_line = ", ".join(grp)
                with col:
                    st.markdown("<div class='group-card'>", unsafe_allow_html=True)
                    st.markdown(f"<h1 class='grp' style='color:{color}'>Gruppe {idx+1}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<h3 class='grp'><em>Antall {len(grp)}</em></h3>", unsafe_allow_html=True)
                    st.markdown(f"<h2 class='grp'>{names_line}</h2>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Presentasjonsmodus: bare grupper ----------
if st.session_state["present"]:
    st.markdown('<div class="app-title">🎲 Suderduper random gruppe</div>', unsafe_allow_html=True)
    st.caption("Presentasjonsmodus – viser kun grupper. Rull for å se alle.")
    if st.session_state["groups"]:
        groups = st.session_state["groups"]
        colors = st.session_state.get("group_colors") or make_random_group_colors(len(groups), random.Random())
        st.success(f"{len(groups)} grupper · {sum(len(g) for g in groups)} elever")
        render_groups(groups, colors)
        if st.button("↩️ Tilbake til redigering"):
            st.session_state["present"] = False
            st.rerun()
    else:
        st.info("Ingen grupper å vise. Gå tilbake og generér grupper først.")
        if st.button("↩️ Tilbake"):
            st.session_state["present"] = False
            st.rerun()
    st.stop()

# ---------- Normalmodus (input + grupper) ----------
st.markdown('<div class="app-title">🎲 Suderduper random gruppe</div>', unsafe_allow_html=True)
st.caption("Lim inn navn, velg antall per gruppe, og (valgfritt) elever som må plasseres i **forskjellige** grupper.")

st.subheader("1) Navneliste")
names_text = st.text_area(
    "Navn (ett per linje eller separert med komma/semikolon):",
    height=170,
    placeholder="Ola Nordmann\nKari Nordmann\nAli Khan\nMina Liu\n…",
    label_visibility="collapsed",
)

st.subheader("2) Elever som må være i ulike grupper (valgfritt)")
sep_text = st.text_area(
    "Disse fordeles først, én per gruppe:",
    height=110,
    placeholder="Per, Lise, Ahmed …",
)

c1, c2, c3, c4 = st.columns([1,1,1,1.2])
with c1:
    group_size = st.number_input("Antall personer per gruppe", 2, 20, 4, 1)
with c2:
    use_seed = st.toggle("Bruk frø (samme grupper og farger igjen)")
with c3:
    seed_val = st.number_input("Frøverdi", 0, 10000, 42, 1, disabled=not use_seed)
with c4:
    present_btn = st.button("🎥 Presentasjonsmodus (kun grupper)")

generate = st.button("✨ Generer grupper")

if present_btn:
    if st.session_state.get("groups"):
        st.session_state["present"] = True
        st.rerun()
    else:
        st.warning("Generér grupper først.")

if generate:
    all_names = parse_names(names_text)
    sep_names = parse_names(sep_text)
    if not all_names:
        st.warning("Legg inn minst ett navn.")
    else:
        n_groups = math.ceil(len(all_names) / group_size)
        targets = planned_group_sizes(len(all_names), n_groups)
        rng = random.Random(seed_val if use_seed else None)
        try:
            groups = distribute_with_separation(all_names, sep_names, targets, rng)
            st.session_state["groups"] = groups
            st.session_state["group_colors"] = make_random_group_colors(len(groups), rng)
        except ValueError as e:
            st.session_state["groups"] = None
            st.session_state["group_colors"] = None
            st.error(str(e))

# Vis grupper i normalmodus
if st.session_state.get("groups"):
    groups = st.session_state["groups"]
    colors = st.session_state.get("group_colors") or make_random_group_colors(len(groups), random.Random())
    st.success(f"Laget {len(groups)} grupper for {sum(len(g) for g in groups)} elever (≈{group_size} per gruppe).")
    render_groups(groups, colors)

    # Last ned CSV
    df = groups_to_dataframe(groups)
    st.download_button(
        "⬇️ Last ned grupper (CSV)",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="grupper.csv",
        mime="text/csv",
    )
