from contextlib import nullcontext

import streamlit as st
from lib.utils import load_data, simulation_scenario, select_box, pie_chart, beneficaires, \
    detailed_graph, section_example_cases, detailed_graph_continuous
from lib.tweaker import st_tweaker as stt


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

.title {
   border-bottom: 1px solid grey;
}

[data-testid=metric-container] {
    max-width:200px;
    padding: 0.5em;
    box-shadow: rgba(0, 0, 0, 0.16) 0px 3px 6px, rgba(0, 0, 0, 0.23) 0px 3px 6px;
    border-radius:5px;
}

th {
    font-weight:700 !important;
    color:black !important;
}

.summary {
  padding: 1em;
    padding-top: 1em;
    padding-right: 1em;
    padding-bottom: 1em;
    padding-left: 1em;
  box-shadow: rgba(0, 0, 0, 0.16) 0px 3px 6px, rgba(0, 0, 0, 0.23) 0px 3px 6px;
  border-radius: 5px;

  background-color:#ffe86f;
}

.summary p {
    font-size:1.3rem;
}

"""

ASSIETTES_BAREMES  = {
    "actuel" : ["bareme1"],
    "assiette1" : ["bareme1", "bareme3"],
    "assiette2" : ["bareme4", "bareme2"]
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

# Volume total / flux d'héritage
VOLUME_TOTAL = 300 * 10 **9 # 300 Milliards



def title(label):
    stt.title(label, cls="title")

def section_params(columns=True):
    """ Display and get parameters """
    title("Paramètres")

    st.markdown("""
        Modifiez les paramètres et observez l'impact sur les résultats dans la section suivante. 
    """)


    param_col1, param_col2, param_col3 = st.columns(3) if columns else [nullcontext()] * 3

    with param_col1 :
        help = """
        Les réformes de niches fiscales envisagées par le CAE modulent la part d'héritage imposable. 
        Le CAE propose deux scenarios plus ou moins ambitieux. Cf la [note du CAE](https://www.cae-eco.fr/repenser-lheritage) 
        """

        assiette = select_box(
            "Assiette fiscale",
            ASSIETTES,
            default="assiette2", help=help)

    with param_col2 :
        baremes = {key: BAREMES[key] for key in ASSIETTES_BAREMES[assiette]}

        help="""Ce paramètre modifie les taux d'imposition pour chaque tranche imposable. Là encore, le CAE propose plusieurs scénarios. 
        Cf la [note du CAE](https://www.cae-eco.fr/repenser-lheritage)
        """

        # Les options de barmèe dépendent de l'option d'assiette
        bareme = select_box(
            "Barèmes (taux d'imposition)",
            baremes, help=help)


    with param_col3:
        if assiette == "actuel":
            scenario = "actuel"
        else :
            scenario = "%s-%s" % (assiette, bareme)

        help="""
            Ce paramètre contrôle la manière dont on répartit le surplus de recettes fiscales pour financer un héritage minimal.
             * *égal* : le surplus est réparti de manière égale entre tous les citoyens, quel que soit par ailleurs leur héritage direct.   
             * *équitable* : le surplus est redistribué en priorité à ceux dont l'héritage direct est le plus faible, afin d'arriver au niveau d'héritage des tranches suivantes  
        """

        mode = select_box(
            "Mode de répartition",
            dict(
                egal="égal - :grey[*réparti également entre tous*]",
                equitable="équitable - :grey[*distribué aux plus pauvres pour assurer une base commune*]"),
            default="equitable",
            radio=True,
            help=help)

    return scenario, mode

def section_results(df, scenario, mode, base):

    title("Résultats")

    df, surplus, heritage_min = simulation_scenario(df, scenario, equitable=(mode=="equitable"))

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

    stt.markdown("""
        Ce scenario génère un :red[surplus de recette fiscales de **%d milliards €**].
        
         Il permettrait de financer un :blue[**héritage de base** **%d 000 €**].
         
         Il profiterait à :green[**%d %% de la population**].""" % (surplus_brut / (10**9), heritage_min/1000, nb_benef + nb_neutres),

        cls="summary")

    # Cas d'exemples
    section_example_cases(df, heritage_min)


    st.subheader("Bénéficiaires")
    st.markdown("""
    Ce graphe présente les parts de population qui seraient :
    * **Gagnants** : héritage plus important 
    * **Neutres** : héritage similaire, mais plus précoce (25 ans contre 50 ans en moyenne)
    * **Perdants** : héritage moindre
    """)


    pie = pie_chart(df)
    pie.update_layout(height=300)
    st.plotly_chart(pie, height=300)

    st.subheader("Détails")
    st.markdown(
        """
        Les graphes suivants montrent, pour chaque tranche, l'héritage avant et après réforme. 
        
        Le deuxième graphe est un 'zoom' sur les quantiles 0-90% peu lisibles du fait des fortes inégalités de l'héritage.""")

    detailed_fig = detailed_graph(df, heritage_min)
    st.plotly_chart(detailed_fig)

    detailed_fig = detailed_graph(df, heritage_min, quant_max=90)
    st.plotly_chart(detailed_fig)

    st.plotly_chart(detailed_graph_continuous(df, heritage_min))

def main():

    # Setup app details
    st.set_page_config(
        page_title='Simulateur - Héritage pour tous',
        page_icon="👴")

    # Load static CSS
    st.markdown(f"<style>{STYLE}</style>", unsafe_allow_html=True)

    title("l'Héritage pour tous : simulateur fiscal")

    st.markdown("""

      Ce simulateur reprend l'idée de [l'héritage pour tous de Thomas Picketty](https://www.lemonde.fr/idees/article/2021/05/15/thomas-piketty-l-heritage-pour-tous-vise-a-accroitre-le-pouvoir-de-negociation-de-ceux-qui-ne-possedent-rien_6080270_3232.html) 
     et se base sur les travaux du *Conseil d'Analyse économique* (CAE) : [Repenser l'héritage](https://www.cae-eco.fr/repenser-lheritage).
    
      En réformant la fiscalité sur l'héritage, il est possible de faire un impôt **réellement progressif**, qui **bénéfice à la majorité des français** (jusqu'à 99%), 
     tout en dégageant un **surplus de recettes fiscales** permettant de financer un **héritage minimal socialisé**, versé à tout citoyen au **début de sa vie active** 
     (25 ans par exemple, contre 50 ans en moyenne actuellement).    
    
      L'objectif de ce simulateur est donc de mettre en valeur le travail du CAE qui a démontré la faisabilité d'un tel projet, et d'ouvrir le débat public sur ce sujet.   
    
    """, unsafe_allow_html=True)

    # Load data
    df, SCENARIOS = load_data()

    # Base des tranche statistiques
    base = VOLUME_TOTAL / df.volumes.sum()

    with st.sidebar :
        scenario, mode = section_params(columns=False)

    section_results(df=df, scenario=scenario, mode=mode, base=base)


#  --- Call Main ---


main()



