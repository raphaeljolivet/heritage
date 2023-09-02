import streamlit as st
from lib.utils import load_data, simulation_scenario, select_box, example_cases, pie_chart, beneficaires
from lib.tweaker import st_tweaker as stt

st.title("Simulation d'un héritage de base")

st.markdown("Hello **world**")

STYLE="""
.metric-recettes {
    color:green
}

.metric-heritage-min {
    color:blue
}

.metric-heritage-pct {
    color:green
}

[data-testid=metric-container] {
    max-width:200px;
    padding: 0.5em;
    box-shadow: rgba(0, 0, 0, 0.16) 0px 3px 6px, rgba(0, 0, 0, 0.23) 0px 3px 6px;
    border-radius:5px;
}


"""

ASSIETTES_BAREMES  = {
    "actuel" : ["bareme1"],
    "assiette1" : ["bareme1", "bareme3"],
    "assiette2" : ["bareme2", "bareme4"]
}

ASSIETTES = dict(
    actuel="Système actuel",
    assiette1="Assiette 1",
    assiette2="Assiette 2")

BAREMES = dict(
    bareme1="Barème actuel",
    bareme2="Barème 2 (même taux effectifs que le système actuel)",
    bareme3="Barème 3 : Taux effectif inchangé pour 99% des héritiers. Surtaxe pour 1%",
    bareme4="Barème 4 : Baisse des droits de succession pour héritages < 4 M€"
)

# Load static CSS
st.markdown(f"<style>{STYLE}</style>", unsafe_allow_html=True)

# Load data
df, SCENARIOS = load_data()

print("Scenarios", SCENARIOS)

# Volume total / flux d'héritage
volume_total = 300 * 10**9

# Base des tranche statistiques
base = volume_total / df.volumes.sum()

with st.sidebar:
    assiette = select_box(
        "Assiette fiscale",
        ASSIETTES,
        default="assiette2")

    baremes = {key: BAREMES[key] for key in ASSIETTES_BAREMES[assiette]}

    # Les options de barmèe dépendent de l'option d'assiette
    bareme = select_box(
        "Barèmes (taux d'imposition)",
        baremes)

    if assiette == "actuel":
        scenario = "actuel"
    else :
        scenario = "%s-%s" % (assiette, bareme)



st.title("Résultats")

df, fig, surplus, heritage_min = simulation_scenario(df, scenario)

nb_benef, nb_neutres, nb_perdant = beneficaires(df)

surplus_brut = surplus * base

col1, col2, col3 = st.columns(3)


with col1 :
    stt.metric(
        "Recettes supplémentaires", "+%d Md€" % (surplus_brut / (10**9)),
        cls="metric-recettes")

with col2 :
    stt.metric(
        "Héritage de base", "%d k€" % (heritage_min / 1000),
        cls="metric-heritage-min")

with col3 :
    stt.metric(
        "% de population gagnante", "%d %%" % (nb_benef + nb_neutres),
        cls="metric-heritage-pct")

stt.markdown(
    "Ce scenario génère un :green[surplus de recette fiscales de **%d milliards €**], qui permettrait de financer un héritage de base de :blue[**%d 000 €**]. "
    "Il profiterait à :green[**%d %% de la population**]." %
            (surplus_brut / (10**9), heritage_min/1000, nb_benef + nb_neutres))

st.subheader("Cas d'exemple")

st.markdown("Voici quelques cas d'exemples d'héritage avant/après une réforme de la fiscalité : ")

examples_df = example_cases(df, heritage_min)
st.table(examples_df)

st.subheader("Bénéficiaires")
st.markdown(
    "Ce graphe présente les parts de population qui seraient **gagnants**, **perdants** ou **neutres** par l'application d'une telle réforme."
    "Notons que mêmes les tranches 'neutres' en terme d'héritage net reçu, bénéficieraient d'un **héritage précoce** de la part minimale socialisée.")


pie = pie_chart(df)
pie.update_layout(height=300)
st.plotly_chart(pie, height=300)

st.subheader("Détails")
st.markdown("Ce graphe montre, pour chaque tranche, l'héritage avant et après réforme.")
st.plotly_chart(fig)

