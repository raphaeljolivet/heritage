import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import plotly.express as px

def compute_volumes(df) :

    quantiles = np.insert(df.index.values, 0, [0])
    df["pct"] = quantiles[1:] - quantiles[0:-1] # largeur de l'intervale
    df["volumes"] = df.heritage.values * (quantiles[1:] - quantiles[0:-1]) / 100
    df["volumes_brut"] = df.volumes * 100 / (100 - df.actuel)
    df["heritage_brut"] = df.heritage * 100 / (100 - df.actuel)
    return df


def load_data() :

    df_herit = pd.read_csv("data/heritage.csv", comment="#")
    df_herit = df_herit.rename(columns={key: key.split("[")[0] for key in df_herit.columns})
    df_herit.quant = df_herit.quant
    df_herit = df_herit.set_index("quant")

    # Read taux effectif
    df_taux = pd.read_csv("data/taux_effectifs.csv", comment="#")
    df_taux = df_taux.rename(columns={key: key.split("[")[0] for key in df_taux.columns})
    df_taux.quant = df_taux.quant
    df_taux = df_taux.set_index("quant")

    scenarios = list(df_taux.columns)

    # Jointure des deux ensembles de données
    df = df_herit.join(df_taux)

    df = compute_volumes(df)

    return df, scenarios


def heritage_de_base(df, surplus, base=1):
    """Calcul de l'héritage de base finançable avec un surplus donné"""

    quant = np.insert(df.index.values, 0, [0])

    # Taille chaque segment
    # XXX hardcodé à 0.1 (premier quantiles considéres uniquement)
    width = 0.1

    heritages = df.heritage.values

    # Boucle sur les quantiles : tant que l'héritage min déborde sur le suivant
    for i in range(len(heritages)):

        if (quant[i + 1] - quant[i]) / 100 != width:
            raise Exception("Pas d'héritage minimum trouvé pour les premiers quantiles")

        heritage_min = (surplus / (width * base) + np.sum(heritages[0:i])) / (i + 1)

        print("Quantile %d%%-%d%%. Héritage min :%d" % (quant[i + 1], quant[i], heritage_min))

        if heritage_min < heritages[i + i]:
            break
        else:
            print("> %d => continue" % heritages[i + 1])

    return heritage_min


def beneficaires(df):
    """Computes share of beneficaries"""

    loosers = 0
    winners=0
    neutrals=0

    for row in df.to_dict(orient="records"):
        if row["sign"] > 0 :
            winners += row["pct"]
        elif row["sign"] < 0 :
            loosers += row["pct"]
        else:
            neutrals += row["pct"]

    return winners, neutrals, loosers


def pie_chart(df) :
    values = beneficaires(df)

    fig = px.pie(
        values=values,
        names=["Héritage + important", "Héritage identique et + précoce", "Héritage moindre"],
        color_discrete_sequence=["green", "blue", "orange"])
    fig.update_traces(sort=False)
    return fig


def simulation_scenario(df, scenario, equitable=True):

    """Calcul le surplus de recettes pour un scenario """

    df = df.copy()

    # Calcul des volumes brut et héritages bruts
    df["volumes_brut"] = df.volumes * 100 / (100 - df.actuel)
    df["heritage_brut"] = df.heritage * 100 / (100 - df.actuel)

    # Calcul du surplus
    surplus = np.sum(df["volumes_brut"] * (df[scenario] - df.actuel) / 100)

    print("Surplus moyen", surplus)

    df["nouveau_net"] = df["heritage_brut"] * (1 - df[scenario] / 100)

    # Mode de redistribution
    if equitable :
        heritage_min = heritage_de_base(df, surplus)
        df["nouveau_net"] = np.maximum(df["nouveau_net"], heritage_min)
    else:
        # Egal
        heritage_min = surplus
        df["nouveau_net"] += surplus

    # Diff entre ancien et nouvel héritage, à 5% prêt
    df["sign"] = df.apply(lambda row : compare(row["heritage"], row["nouveau_net"]), axis=1)

    return df, surplus, heritage_min

def rates_graph(df, scenario) :

    fig = go.Figure()



    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["actuel"],
        name='Avant réforme',
        mode='lines',
        marker_color='orange',
        marker={"line": {"width": 2, "color": "orange"}}
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[scenario],
        name='Après réforme',
        mode='lines',
        marker_color='green',
        marker={"line": {"width": 2, "color": "green"}}
    ))

    fig.update_layout(
        title="Taux d'imposition par héritage",
        xaxis=dict(title='Part de la population (%)'),
        yaxis=dict(
            title="Taux d'imposition (%)",
            titlefont_size=16,
            tickfont_size=14,
        )
    )

    return fig

def _compute_quantiles_str(df):

    quantiles = np.insert(df.index.values, 0, [0])
    quantiles_str = []
    for i, quant in enumerate(quantiles):
        if i >= len(df):
            break
        if quant < 99:
            quant2 = quantiles[i + 1]
            quantiles_str.append("%d-%d %%" % (quant, quant2))
        else:
            quantiles_str.append(">%0.1f %%" % (100 - quant))
    return quantiles_str

def detailed_graph(df, heritage_min, quant_max=None) :

    if quant_max :
        df = df[df.index <= quant_max]

    quantiles_str = _compute_quantiles_str(df)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=quantiles_str,
                             y=[heritage_min] * len(quantiles_str),
                             name='Héritage de base (%d k€)' % (heritage_min / 1000),
                             line_color='red',
                             mode='lines',
                             line_dash='dash',
                             ))

    fig.add_trace(go.Bar(x=quantiles_str,
                         y=df.heritage,
                         name='Avant réforme',
                         marker_color='orange',
                         marker={"line": {"width": 2, "color": "orange"}}
                         ))

    fig.add_trace(go.Bar(x=quantiles_str,
                         y=df.nouveau_net,
                         name='Après réforme',
                         marker_color='green',
                         marker = {"line": {"width": 2, "color": "green"}}
                         ))

    title_prefix = "[Zoom 0-%d%%] " % (quant_max) if quant_max else ""

    fig.update_layout(
        title=title_prefix + 'Héritage avant et après réforme de la fiscalité, pour chaque tranche',
        xaxis_tickfont_size=14,
        xaxis=dict(
            title='Part de la population',
            tickangle=-45),
        yaxis=dict(
            title='Héritage net €',
            titlefont_size=16,
            tickfont_size=14,
        ),
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)'
        ),
        barmode='group',
        # bargap=0.15, # gap between bars of adjacent location coordinates.
        # bargroupgap=0.1 # gap between bars of the same location coordinate.
    )

    return fig

def detailed_graph_splitted(df) :

    quantiles = np.insert(df.index.values, 0, [0])
    #quantiles_str = []
    #for i, quant in enumerate(quantiles):
    #    if i >= len(df):
    #        break
    #    if quant < 99:
    #        quant2 = quantiles[i + 1]
    #        quantiles_str.append("%d-%d %%" % (quant, quant2))
    #    else:
    #        quantiles_str.append(">%0.1f %%" % (100 - quant))

    #fig = make_subplots(rows=2, cols=1, vertical_spacing = 0.04)
    fig = go.Figure()

    """
    fig.add_trace(go.Scatter(
            x=quantiles,
            y=df.heritage,
            name='Héritage',
            marker_color='orange',
            marker={"line": {"width": 2, "color": "orange"}}),
        row=2, col=1)"""

    fig.add_trace(go.Scatter(
        x=quantiles/100,
        y=df.heritage,
        name='Héritage',
        marker_color='orange',
        marker={"line": {"width": 2, "color": "orange"}}))

    fig.update_layout(
        xaxis_tickfont_size=14,
        xaxis=dict(
            title='Part de la population',
            tickformat=".0%",
        ),
        yaxis=dict(
            title='Héritage net € (log)',
            titlefont_size=16,
            tickfont_size=14,
            type="log",
        ),
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)'
        ),
        barmode='group',
        # bargap=0.15, # gap between bars of adjacent location coordinates.
        # bargroupgap=0.1 # gap between bars of the same location coordinate.
    )

    #fig.update_yaxes(range=[CUT_INTERVAL[1], df.heritage.max() * 1.1], row=1, col=1)
    #fig.update_xaxes(visible=False, row=1, col=1)
    #fig.update_yaxes(range=[0, CUT_INTERVAL[0]], row=2, col=1)

    return fig


def detailed_graph_continuous(df, heritage_min) :

    quantiles = np.insert(df.index.values, 0, [0])

    quant_width = np.array([quantiles[i+1]-quantiles[i] for i in range(0, len(quantiles)-1)])

    volumes = df.heritage * quant_width

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=quantiles,
                             y=[heritage_min] * len(quantiles),
                             name='Héritage de base (%d k€)' % (heritage_min / 1000),
                             line_color='red',
                             mode='lines',
                             line_dash='dash'
                             ))

    fig.add_trace(go.Scatter(x=quantiles,
                         y=volumes,
                         mode='lines',
                         name='Avant réforme',
                         line_color='rgb(55, 83, 109)'
                         ))

    fig.update_layout(
        title='Héritage avant et après réforme de la fiscalité, pour chaque tranche',
        xaxis_tickfont_size=14,
        xaxis=dict(
            title='Part de la population'),
        yaxis=dict(
            title='Héritage net €',
            #type='log',
            titlefont_size=16,
            tickfont_size=14,
        ),
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)'
        ),
    )

    return fig

def select_box(label, dict_values, default=None, radio=False, help=None) :

    if default is not None:
        index = list(dict_values.keys()).index(default)
    else:
        index=0

    func = st.radio if radio else st.selectbox


    return func(
        label,
        dict_values.keys(),
        format_func=lambda key : dict_values[key],
        index=index,
        help=help)


def compare(before, after) :
    """ Compare two numbers with 5% tolerance"""

    pct = (after - before) / before * 100
    if pct < -5 :
       return -1
    elif pct > 5:
       return 1
    else :
       return 0

def compare_symbol(before, after, neutral_symbol="😐") :
    sign = compare(before, after)
    if sign == -1 :
        return "😒"
    elif sign == 1 :
        return "😊"
    else:
        return neutral_symbol

def format_amount(amount) :
    if amount < 1000:
        return "%d €" % amount
    elif amount < 1000000:
        return "%d 000 €" % (amount / 1000)
    else:
        return "%d M€" % (amount / 10**6)

def section_example_cases(df, heritage_min) :

    IDX_PAUVRE=0
    IDX_MOYEN=6
    IDX_RICHE=12

    net_before = df.heritage.values
    net_after = df.nouveau_net.values

    before_labels = []
    after_labels = []

    for idx in [IDX_PAUVRE, IDX_MOYEN, IDX_RICHE] :
        before_amount = net_before[idx]
        after_amount = net_after[idx]
        symbol = compare_symbol(
            before_amount,
            after_amount,
            neutral_symbol="😊")

        before_labels.append(
            format_amount(before_amount) + (" ( à 50 ans 👴🏻)" if before_amount > 1000 else ""))

        after_labels.append(
            symbol + " " + format_amount(after_amount) + f" (dont {int(heritage_min/1000)} k€ à 25 ans)"
        )

    df = pd.DataFrame({
            "Profil": ["Aucun héritage ", "Héritage moyen 💰", "Gros héritage 💰💰💰"],
            "Avant réforme": before_labels,
            "Après réforme": after_labels,
        }).set_index("Profil")

    st.subheader("Cas d'exemple")
    st.markdown("Voici quelques cas d'exemples d'héritage avant/après une réforme de la fiscalité : ")

    st.table(df)