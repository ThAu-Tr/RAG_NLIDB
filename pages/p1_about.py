import streamlit as st
import pandas as pd
from scripts import vanna_calls_ds as vc

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

def create_decarbonization_plot(df):
    fig = go.Figure()

    # Stacked bar chart for percentages
    fig.add_trace(go.Bar(
        x=df['quarter'], y=df['Fossil_Percentage'],
        name='Fossil %', marker_color= "#E07A7A", # Soft Red
        text= df['Fossil_Percentage'].round(2).astype(str) + '%'
        
    ))
    fig.add_trace(go.Bar(
        x=df['quarter'], y=df['Renewable_Percentage'],
        name='Renewable %', marker_color= "#8CCF9E", # Soft Green
        text= df['Renewable_Percentage'].round(2).astype(str) + '%'

    ))
    fig.add_trace(go.Bar(
        x=df['quarter'], y=df['Nuclear_Percentage'],
        name='Nuclear %', marker_color= "#6FA8DC", # Soft Blue
        text= df['Nuclear_Percentage'].round(2).astype(str) + '%'

    ))

    # Line chart for total emissions
    #fig.add_trace(go.Scatter(
        #x=df['quarter'], y=df['total_emissions'],
        #name='Total Emissions (MtCO2e)', mode='lines+markers',
        #yaxis='y2', line=dict(color="#292525", width=3) # Cyan line
    #))

    # Line chart for emissions
    fig.add_trace(go.Scatter(
        x=df['quarter'],
        y=df['total_emissions'],
        name='Total Emissions (MtCO2e)',
        mode='lines+markers',
        line=dict(color='black')
    ))

    # Update layout
    fig.update_layout(
        barmode='stack',
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title='Percentage (%)', range=[0, 100]),
        yaxis2=dict(title='Emissions (MtCO2e)', overlaying='y', side='right', showgrid=False, zeroline=False),
        xaxis=dict(title='Quarter'),
        margin=dict(l=20, r=20, t=50, b=20),
        height=500
    )
    return fig

def create_potential_gap_plot(df):
    """
    Erstellt ein Dumbbell-Plot (Hantel-Diagramm), um die tatsächliche Wind-Erzeugung 
    mit der simulierten Erzeugung (Generation Capability) zu vergleichen.
    """
    fig = go.Figure()

    # 1. Punkte für die tatsächliche Erzeugung (Frankreich)
    fig.add_trace(go.Scatter(
        x=df['actual_wind_generation'],
        y=df['season'],
        mode='markers',
        name='Actual Wind Generation (FR)',
        marker=dict(color='blue', size=10),#color='#2c3e50', size=12),
        hovertemplate='Tatsächlich: %{x:.2f} TWh<extra></extra>'
    ))

    # 2. Punkte für die simulierte Erzeugung (Benchmark DE)
    fig.add_trace(go.Scatter(
        x=df['simulated_generation'],
        y=df['season'],
        mode='markers',
        name='Simulated (DE Capability)',
        marker=dict(color='orange', size=10),#'#e67e22', size=12),
        hovertemplate='Simuliert: %{x:.2f} TWh<extra></extra>'
    ))

    # 3. Verbindungslinien und Prozent-Labels
    for i in range(len(df)):
        # Wir nutzen iloc, um sicherzugehen, dass wir die richtige Zeile erwischen
        row = df.iloc[i]
        
        # Die "Hantel-Stange"
        fig.add_trace(go.Scatter(
            x=[row['actual_wind_generation'], row['simulated_generation']],
            y=[row['season'], row['season']],
            mode='lines',
            line=dict(color='gray',width=2),#'#bdc3c7', width=3),
            showlegend=False,
            hoverinfo='skip'
        ))

        # Das Prozent-Label mittig über der Linie
        fig.add_trace(go.Scatter(
            x=[(row['actual_wind_generation'] + row['simulated_generation']) / 2],
            y=[row['season']],
            text=[f"+{row['potential_gap_percentage']:.1f}%"],
            mode='text',
            textposition="top center",
            #textfont=dict(color='#e67e22', size=12, family="Arial Black"),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Layout-Optimierung für die Landing Page
    fig.update_layout(
        #title=dict(
            #text='<b>Potential Growth Gap:</b> Windkraft-Potenzial Frankreichs',
            #x=0.5,
            #xanchor='center'
        #),
        xaxis_title='Generation (TWh)',
        yaxis_title='Season',
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#ecf0f1', zeroline=False),
        yaxis=dict(tickmode='linear', autorange="reversed"), # Optional: Winter oben
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def render_minimal_energy_mix(df):
    """
    Renders a clean, label-only chart without a title or legend.
    Perfect for embedding in small Streamlit cards or sidebars.
    """
    color_map = {
        "Wind": "light purple",
        "Biomass": "green",
        "Solar": "orange",
        "Hydro": "red",
    }
    
    if df.empty:
        st.warning("No data available.")
        return None

    if len(df) == 1:
        source = df["energy_source"].iloc[0]
        source_color = color_map.get(source, "black") # Default to black if not found
        
        fig = go.Figure(
            go.Indicator(
                mode="number",
                value=df["generation_mwh"].iloc[0],
                # Keeps the text identifier but removes the formal 'title' block
                title={"text": str(df["energy_source"].iloc[0]), "font": {"size": 20, "color": source_color}},
                number={'valueformat': ',.0f', 'font': {'color': source_color}}
            )
        )
    else:
        colors = [color_map.get(label, "grey") for label in df["energy_source"]]

        fig = go.Figure(
            go.Pie(
                labels=df["energy_source"],
                values=df["generation_mwh"],
                marker=dict(colors=colors),  # <--- APPLY COLORS HERE
                hole=0.4,
                sort=True,        # Set to True so it orders from largest to smallest
                rotation=85,      # 90 degrees forces the first slice to start at 12 o'clock (North)
                direction='clockwise', # Draws the slices clockwise from the top
                showlegend=False
            )
        )
        fig.update_traces(textinfo="percent+label")

    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, l=0, r=0, b=0),
        height=185,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig

def render_portfolio_map(df):
    if df is None or df.empty:
        return None

    df_plot = df.copy()

    # FIX 1: Create the combined string column BEFORE the px call
    df_plot["hover_title"] = df_plot["company_name"] + " | " + df_plot["city"]

    # KPI View (Single Row)
    if len(df_plot) == 1:
        row = df_plot.iloc[0]
        fig = go.Figure(
            go.Indicator(
                mode="number",
                value=float(row["total_generation_capacity_mw"]),
                title={"text": f"{row['hover_title']}<br>{row['energy_source_name']}"}
            )
        )
    
    # Map View (Multiple Rows)
    else:
        color_map = {
            "Wind": "#B39DDB",
            "Biomass": "#2E7D32",
            "Solar": "#FB8C00",
            "Hydro": "#C62828",
        }

        # FIX 2: Use "total_generation_capacity_mw" (exactly as in beispiel1.csv)
        fig = px.scatter_mapbox(
            df_plot,
            lat="latitude",
            lon="longitude",
            color="energy_source_name",
            color_discrete_map=color_map,
            size="total_generation_capacity_mw", 
            size_max=40,
            zoom=5,
            height=700,
            #map_style="carto-positron",
            hover_name="hover_title",  # Use the column we created above
            hover_data={
                "tso_region": True,
                "total_generation_capacity_mw": ":.2f",
                "asset_count": True,
                "latitude": False,
                "longitude": False,
                "hover_title": False,
                "energy_source_name": True
            },
            labels={
                "energy_source_name": "Energy Source",
                "total_generation_capacity_mw": "Capacity (MW)",
                "asset_count": "Assets",
                "tso_region": "TSO Region",
            },
        )

    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        mapbox_style="carto-positron"
    )

    return fig


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def create_generation_yoy_plot(df: pd.DataFrame):
    """
    Generates a Plotly figure for YoY analysis. 
    Returns an Indicator for single records or a Subplot for time-series data.
    """
    if df.empty:
        return go.Figure().update_layout(title="No data available")

    # CASE 1: Single Record (e.g., a specific month or year total)
    if len(df) == 1:
        row = df.iloc[0]
        fig = go.Figure(
            go.Indicator(
                mode="number+delta",
                value=row["generation_mwh_2025"],
                delta={"reference": row["generation_mwh_2024"], "valueformat": ".2f"},
                title={"text": f"{row['month_name']} Generation (2025 vs 2024)"},
            )
        )
        fig.update_layout(height=400)

    # CASE 2: Multi-row Data (Time-series / Month-over-Month)
    else:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            subplot_titles=("Generation MWh (2024 vs 2025)", "YoY Growth MWh"),
            specs=[[{}], [{}]],
        )

        # Trace 1: 2024 Line
        fig.add_trace(
            go.Scatter(
                x=df["month_name"],
                y=df["generation_mwh_2024"],
                mode="lines+markers",
                name="Generation 2024",
                line=dict(color="#636EFA")
            ),
            row=1, col=1,
        )

        # Trace 2: 2025 Line
        fig.add_trace(
            go.Scatter(
                x=df["month_name"],
                y=df["generation_mwh_2025"],
                mode="lines+markers",
                name="Generation 2025",
                line=dict(color="#EF553B")
            ),
            row=1, col=1,
        )

        # Trace 3: YoY Absolute Growth Bar
        fig.add_trace(
            go.Bar(
                x=df["month_name"],
                y=df["yoy_growth_mwh"],
                name="YoY Growth MWh",
                marker_color="#00CC96",
                text=df["yoy_growth_pct"].map(lambda v: f"{v:.1f}%"),
                textposition="outside",
                hovertemplate="Month: %{x}<br>YoY Growth MWh: %{y:,.2f}<br>YoY Growth %: %{text}<extra></extra>",
            ),
            row=2, col=1,
        )

        # Axis and Layout Updates
        fig.update_xaxes(title_text="Month", row=2, col=1)
        fig.update_yaxes(title_text="MWh", row=1, col=1)
        fig.update_yaxes(title_text="Growth MWh", row=2, col=1)

        fig.update_layout(
            template="plotly_white",
            legend_title_text="",
            height=800,
            margin=dict(t=80, l=60, r=30, b=60),
            hovermode="x unified"
        )

    return fig

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def create_energy_source_breakdown_plot(df: pd.DataFrame):
    """
    Generates a breakdown plot comparing YoY growth (MWh and %) across different energy sources.
    Uses bars for individual sources and a line for the 'Total Renewables' baseline.
    """
    if df.empty:
        return go.Figure().update_layout(title="No data available")

    # Ensure consistent ordering (Month then Source)
    df = df.sort_values(["month", "energy_source_name"])

    # CASE 1: Single row (KPI Card)
    if len(df) == 1:
        row = df.iloc[0]
        fig = go.Figure(
            go.Indicator(
                mode="number",
                value=row["yoy_growth_mwh"],
                title={"text": f'{row["energy_source_name"]} - YoY Growth MWh'},
            )
        )
        fig.update_layout(height=400)

    # CASE 2: Multi-row (Breakdown Plot)
    else:
        colors = {
            "Wind": "plum",
            "Biomass": "green",
            "Solar": "orange",
            "Hydro": "red",
            "Total Renewables": "black",
        }
        
        # List of sources to iterate over for bars
        sources = ["Wind", "Biomass", "Solar", "Hydro"]

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("YoY Growth MWh", "YoY Growth %"),
        )

        # 1. Add Bars for individual sources
        for source in sources:
            d = df[df["energy_source_name"] == source]
            if not d.empty:
                # Row 1: Absolute Growth
                fig.add_trace(
                    go.Bar(
                        x=d["month"],
                        y=d["yoy_growth_mwh"],
                        name=source,
                        marker_color=colors.get(source, "lightgrey"),
                        legendgroup=source,
                        showlegend=True,
                    ),
                    row=1, col=1,
                )
                # Row 2: Percentage Growth
                fig.add_trace(
                    go.Bar(
                        x=d["month"],
                        y=d["yoy_growth_pct"],
                        name=source,
                        marker_color=colors.get(source, "lightgrey"),
                        legendgroup=source,
                        showlegend=False,
                    ),
                    row=2, col=1,
                )

        # 2. Add 'Total Renewables' as a trendline on both subplots
        d_total = df[df["energy_source_name"] == "Total Renewables"]
        if not d_total.empty:
            # Trendline Row 1
            fig.add_trace(
                go.Scatter(
                    x=d_total["month"],
                    y=d_total["yoy_growth_mwh"],
                    name="Total Renewables",
                    mode="lines+markers",
                    line=dict(color=colors["Total Renewables"], width=3),
                    legendgroup="Total Renewables",
                    showlegend=True,
                ),
                row=1, col=1,
            )
            # Trendline Row 2
            fig.add_trace(
                go.Scatter(
                    x=d_total["month"],
                    y=d_total["yoy_growth_pct"],
                    name="Total Renewables",
                    mode="lines+markers",
                    line=dict(color=colors["Total Renewables"], width=3),
                    legendgroup="Total Renewables",
                    showlegend=False,
                ),
                row=2, col=1,
            )

        # Layout & Axis Formatting
        fig.update_layout(
            barmode="group",
            template="plotly_white",
            height=800,
            legend=dict(title="Energy Source"),
            margin=dict(t=80, l=60, r=30, b=50),
            hovermode="x unified"
        )

        fig.update_xaxes(title_text="Month", row=2, col=1, dtick=1)
        fig.update_yaxes(title_text="MWh", row=1, col=1)
        fig.update_yaxes(title_text="Growth %", row=2, col=1)

    return fig

def create_monthly_metrics_plot(df: pd.DataFrame) -> go.Figure:
    """Generates a multi-row performance plot comparing monthly YoY trends

    for MWh growth, installed capacity variance, and wind power density.
    Uses an indicator card fallback for single-month queries.
    """
    # Defensive Check: Handle empty inputs safely
    if df.empty:
        return go.Figure().update_layout(title="No data available")

    # Ensure consistent chronological ordering
    df = df.sort_values("month")

    # CASE 1: Single row (KPI Card Fallback)
    if len(df) == 1:
        row = df.iloc[0]
        fig = go.Figure(
            go.Indicator(
                mode="number+delta",
                value=row["yoy_growth_mwh"],
                title={"text": "Monthly Performance Baseline - YoY Growth MWh"},
            )
        )
        fig.update_layout(height=400, template="plotly_white")

    # CASE 2: Multi-row (Full Landing Page Visualization)
    else:
        # --- Original Code Layout Starts Here ---
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=[
                "YoY Growth (MWh)",
                "YoY Difference in Installed Capacity (MW)",
                "YoY Difference in Avg Wind Power Density (W/m²)",
            ],
        )

        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df["yoy_growth_mwh"],
                mode="lines+markers",
                name="YoY Growth (MWh)",
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df["yoy_diff_installed_capacity_mw"],
                mode="lines+markers",
                name="YoY Difference in Installed Capacity (MW)",
            ),
            row=2,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df["yoy_diff_avg_wind_power_density_w_per_m2"],
                mode="lines+markers",
                name="YoY Difference in Avg Wind Power Density (W/m²)",
            ),
            row=3,
            col=1,
        )

        fig.update_layout(
            title="Monthly Results",
            height=900,
            width=1000,
            showlegend=False,
            template="plotly_white",  # Keeps it modern and matched to your style
            hovermode="x unified",
        )

        fig.update_xaxes(title_text="Month", row=3, col=1)
        fig.update_yaxes(title_text="MWh", row=1, col=1)
        fig.update_yaxes(title_text="MW", row=2, col=1)
        fig.update_yaxes(title_text="W/m²", row=3, col=1)
        # --- Original Code Layout Ends Here ---

    return fig

st.set_page_config(layout="centered")
# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("Interaktiver NLIDB-Prototyp")

st.caption(
    "Entwickelt auf Basis der RAG-Architektur – "
    "im Rahmen einer Masterarbeit."
)

col1, col2 = st.columns([1.4, 1])

with col1:
    st.markdown("""
Dieses System ist ein Prototyp für eine **natürlichsprachliche
Datenbankschnittstelle (Natural Language Interface to Databases, NLIDB)**.
Es ermöglicht, relationale Datenbanken mithilfe **natürlicher Sprache**
zu befragen und zu analysieren – ohne SQL-Kenntnisse vorauszusetzen.
""")

    st.markdown("""
Der Prototyp basiert auf einer **Retrieval-Augmented-Generation-Architektur (RAG)**,
bei der ein **kompaktes Sprachmodell (Small Language Model, SLM)** durch anfragerelevante *Datenbankschemata*, *SQL-Beispiele* und *Kontextinformationen* untestützt wird.
Dies ermöglicht eine präzisere SQL-Generierung sowie die anschließende Datenzusammenfassung und Visualisierung.
""")

with col2:
    # 3. THE CSS WRAPPER HACK
    st.markdown("""
    <div style="
        background-color:#e8f2ff;
        padding:20px;
        border-radius:10px;
        border:1px solid #cfe3ff;
        height: 330px;         /* Make box tall enough to hold the chart */
        margin-bottom: -220px; /* Pull the chart UP into the blue box */
        position: relative;
        z-index: 0;
    ">
    <b>❓ Beispielanfrage:</b><br>
    „Provide a breakdown of the renewable energy mix for 2025 with a donut chart.“
    </div>
    """, unsafe_allow_html=True)
    
    df_step0 = pd.read_csv("assets/df_step0.csv", index_col=0)
    
    # 4. RENDER CHART
# 1. Get the figure from the function
    fig = render_minimal_energy_mix(df_step0)
    
    # 2. Only plot if a figure was actually returned
    if fig:
        st.plotly_chart(fig, use_container_width=True, theme=None, key="mix_chart")    #st.info("""**❓ Beispielanfrage:**  
    #        „Provide a breakdown of the renewable energy mix for 2025 with a donut chart.“""")
    



#st.markdown("""
#Dieses System ist ein Prototyp für eine **natürlichsprachliche
#Datenbankschnittstelle (Natural Language Interface to Database, NLIDB)**. Es ermöglicht, relationale Datenbanken mithilfe
#**natürlicher Sprache** zu befragen und zu analysieren – ohne SQL-Kenntnisse
#vorauszusetzen.
#""")

st.markdown(#"""
#Der Prototyp basiert auf einer **Retrieval-Augmented-Generation-Architektur (RAG)**, bei der ein Sprachmodell durch *Datenbankschema, SQL-Beispiele und Kontextinformationen* unterstützt wird.  
"""
Im Verlauf der Entwicklung entstanden drei aufeinander aufbauende Systemstufen:  
- **Query-System** - Generiert SQL-Abfragen aus natürlichen Fragen  
- **Dialog-System** - Unterstützt mehrstufige Anfragen unter Einbezug des Gesprächskontexts 
- **Assistance-System** - Erweitert die Funktionalität um Exploration, Interpretation und Analyse der Daten  

Gemeinsam verdeutlichen diese Stufen, wie sich auf Basis moderner Sprachmodelle schrittweise ein interaktives Analysewerkzeug entwickeln lässt. 
""")

# --------------------------------------------------
# Mini Use Case
# --------------------------------------------------
#st.markdown("""
### Beispielhafte Nutzung

#> **„Welche fünf Künstler haben den meisten Umsatz generiert?“**  
#> → automatisch interpretiert, in SQL übersetzt und auf der Datenbank ausgeführt
#""")

st.divider()

# --------------------------------------------------
# Vision & Strategischer Mehrwert
# --------------------------------------------------
with st.expander("💡 Vision"):
    st.markdown("""    
Klassische Reporting-Strukturen stoßen zunehmend an ihre Grenzen: Fachabteilungen benötigen häufig **spontane Ad-hoc-Analysen**, verfügen jedoch meist nur über **vordefinierte Dashboards**. Viele Fragen bleiben dadurch zunächst unbeantwortet oder erfordern zusätzlichen Abstimmungsaufwand, bevor sie in bestehende Reports integriert werden.      
                
Der Prototyp adressiert diese Herausforderungen und verfolgt dabei drei zentrale Ziele:     
- **Schnellere Erkenntnisgewinnung:** Während Data-Pipelines implementiert werden, können Fachbereiche ihre Daten in natürlicher Sprache untersuchen und erste Insights erhalten.  
- **Verbesserte Kommunikation:** Konkrete Abfragen und Ergebnisse helfen dabei, fachliche Anforderungen präziser zu formulieren und Missverständnisse zu reduzieren.  
- **Besseres Verständnis der Datenbasis:** Durch die direkte Interaktion mit der Datenbank können Nutzende Tabellen, Beziehungen und verfügbare Informationen schneller nachvollziehen.  
    
    """)
    
    st.info("""🎯 **Kernidee:**  
Das System ersetzt keine Dashboards oder Reports. Es ergänzt sie um eine **flexible Explorationsebene**, die die Lücke zwischen **Rohdaten und finalem Reporting** schließt und die agile Entwicklung im Datenökosystem unterstützt.
                        """)

# --------------------------------------------------
# System Overview
# --------------------------------------------------
with st.expander("🧩 Systemüberblick"):
    st.markdown("""
Der Prototyp basiert auf einer modularen **RAG-Architektur** mit **dialogischer Erweiterung** sowie **interaktiven Funktionen**.

""")
    st.image('assets/Architektur.png')
    st.divider()
    st.markdown("""
🔧 **Technologiestack**:
- **Frontend - Streamlit**  
                (leichtgewichtiges Python-Framework zur Umsetzung einer schlanken Präsentationsschicht mit zustandsbasierter Interaktion ohne API- oder Routing-Komplexität)
- **Orchestrierung - Vanna-Framework**   
                (Python-native Orchestrierungsschicht mit task-spezifischer Abstraktion für Text-to-SQL, erweitertem RAG-Ansatz sowie anpassbaren Kernkomponenten)
- **Sprachmodell – GPT-5.4 mini / GPT-4o mini**  
                (kompakte Sprachmodelle mit erweiterten Kontextfenstern sowie ausgeprägter Struktur- und Coding-Kompetenzen innerhalb ihrer Größenklassen für eine effiziente Text-to-SQL-Generierung)
- **Vektordatenbank - Qdrant**  
                (Vektorindex mit erweiterbaren Metadaten („Payload“) sowie der Möglichkeit zur Kombination semantischer und filterbasierter Selektion („Hybrid Search“))
- **Relationale Datenbank – DuckDB**  
                (serverlose analytische Datenbank zur Ausführung generierter SQL-Abfragen sowie zur Unterstützung erweiterter Analysefunktionen wie Aggregationen, Window-Analysen und Korrelationen) 
""")

with st.expander("⚙️ Funktionsweise"):
    st.markdown("""                
Das System wurde in drei Entwicklungsstufen konzipiert, die jeweils unterschiedliche Aspekte von NLIDB-Interaktion adressieren: **Generierung, Kontextualisierung und Unterstützung**. 
                """)

    lay1, lay2, lay3 = st.tabs(["Generierung", "Kontextualisierung", "Unterstützung"])

    with lay1:
        st.markdown("""
    #### **Query-System**
    *Modulare, strukturorientierte Text-to-SQL-Pipeline*                
    1. Die natürlichsprachliche Anfrage wird interpretiert und mittels einer auf GPT-4o mini ausgerichteten Prompt-Strategie in eine **vorläufige SQL-Abfrage** überführt.
    2. Aus dieser wird ein **SQL-Skelett** extrahiert, um **Question-SQL-Beispiele** zunächst semantisch zu selektieren und anschließend strukturbasiert zu reranken.
    3. **Tabellenreferenzen** der vorläufigen SQL-Abfrage werden extrahiert, um das dem SLM zu übergebende Schema dynamisch zu reduzieren.
    4. Auf Basis der ausgewählten Beispiele und des reduzierten Schemas wird eine **finale SQL-Abfrage** generiert, ausgeführt und bei Fehlern datenbankgestützt reaktiv revidiert.    
    """)
        st.info("""🎯
    **Kernidee**:  
    Robuste Text-to-SQL-Generierung erfordert neben **semantischer** Ähnlichkeit auch **strukturelle** Vergleichbarkeit von SQL-Mustern.
    """)
        
    with lay2:
        st.markdown("""                
    #### **Dialog-System**
    *Erweiterung der Text-to-SQL-Pipeline um eine strukturierte Kontexthistorie*
    - Mehrstufige Interaktionen werden durch die **Speicherung des Gesprächsverlaufs** in Form strukturierter Dialogue-Turns unterstützt.
    - **Kürzlich vergangene Dialogue-Turns** werden als zusätzlicher Bestandteil in die SQL-Generierung integriert.
    - Tabellenergebnisse werden in kompakter Form (**Data-Summary**) repräsentiert, um den Fokus des SLMs auf relevante Informationen zu erhalten
    - Die **Nutzung der Kontexthistorie** variiert je nach Verarbeitungsschritt innerhalb der Pipeline, um Redundanz und Fehlinterpretationen zu vermeiden.
    """)
        st.info("""🎯
    **Kernidee**:  
    Dialogfähigkeit entsteht durch die **kontrollierte Integration** des Gesprächsverlaufs in die bestehende RAG-Architektur.
    """)
    
    with lay3:
        st.markdown("""                
    #### **Assistance-System**
    *Erweiterung um interaktive Analyse- und Unterstützungsfunktionen*
    - Jede Anfrage wird mit einer **Systeminterpretation** eingeleitet und durch **alternative Fragestellungen** ergänzt.
    - Kontextbasierte **Fragevorschläge** unterstützen eine explorative Datenanalyse
    - Eine integrierte Datenbankansicht mit **dynamischem ER-Diagramm sowie Tabellenvorschauen** ermöglicht strukturelle Orientierung.
    - Tabellenergebnisse können **automatisch visualisiert** und **gezielt angepasst** werden.
    - Generierte SQL-Abfragen lassen sich **strukturiert erläutern**.
    """)
        st.info("""🎯
    **Kernidee**:  
    Das System erweitert die Text-to-SQL-Generierung um **erklärende, explorative und interaktive Funktionen** zur strukturierten Datenanalyse.                
    """)

# --------------------------------------------------
# Case Study
# --------------------------------------------------
with st.expander("📊 Evaluation & Fallstudie"):
    st.markdown("""
Zur Überprüfung der **technischen Leistungsfähigkeit** und **praktischen Wirksamkeit** wurde das System sowohl benchmarkbasiert als auch in einem realitätsnahen Anwendungsszenario evaluiert.
""")
    eval1, eval2 = st.tabs(["Technisch", "Praktisch"])

    with eval1:
        st.markdown("""                
    #### **Evaluation**
    Technische Validierung der Systemarchitektur anhand **etablierter Benchmarks** (Spider & SParC)
    - Vergleich mit (1) der **Standardimplementierung des Vanna-Frameworks** und (2) in externen Studien veröffentlichten **ChatGPT-Ergebnissen**
    - **Einheitliche Neubewertung aller Systeme** auf identischer Bewertungsbasis zur Sicherstellung konsistenter Vergleichbarkeit
    - **Single-Turn Szenario** (Spider): 77,3 % Execution Accuracy  
        → Standardimplementierung: 71,9 % | ChatGPT: 68,4 %
    - **Multi-Turn Szenario** (SParC): 64,7 % Execution Accuracy  
        → Standardimplementierung: 40,3 % | ChatGPT: 60,7 %
    - **Turn-basierte Auswertung** des Dialogverlaufs zeigt einen geringeren Performance-Verlust im Vergleich zur Standardimplementierung und zu ChatGPT 
    """)
        st.info("""🎯
    **Kernergebnis**:  
    Die umgesetzten Architekturentscheidungen liefern **messbare Verbesserungen**, insbesondere im mehrstufigen Szenario.
        """)

    with eval2:

        st.markdown("""            

    #### **Fallstudie**
    Praktische Evaluation mit **echten Nutzenden** in einem **realitätsnahen Anwendungsszenario**                                          

    **Setting**
    - **18 Teilnehmende** mit unterschiedlicher SQL-Vorerfahrung und beruflichem Hintergrund 
    - **Vorstrukturierte Analyseaufgaben** sowie **freie Exploration** auf einer relationalen Beispieldatenbank (Chinook)
    - Vergleich der drei Systemstufen hinsichtlich wahrgenommene   
    a) **Nützlichkeit**, b) **Benutzerfreundlichkeit** sowie c) **Konversations- und Informationsqualität** 
    - Erfassung **qualitativer Rückmeldungen** zu  
    i) Stärken, ii) Schwächen und iii) gewünschten Erweiterungen
                    
    **Zentrale Beobachtungen**
    - Das **Dialog-System** erhielt die höchsten Bewertungen in allen drei Wahrnehmungskriterien und wurde insgesamt als **übersichtlicher** wahrgenommen
    - Das **Assistance-System** erzielte die **beste objektive Aufgabenleistung**, wurde jedoch teilweise als informationsintensiver beschrieben 
    - **Mehrstufige Dialogführung** reduzierte kognitive Belastung und **verbesserte die Orientierung** im Analyseprozess 
    - **Erweiterte Assistenzfunktionen** wurden von **technisch-versierten** Teilnehmenden **geschätzt**, erzeugten jedoch bei einigen **SQL-Unerfahrenen** zusätzliche **Komplexität**
    - Einzelne Teilnehmende wünschten sich eine **Steuerung der Informationsdichte** sowie eine **explizite Sprachauswahl**  
        → **Umsetzung im Prototyp:** konfigurierbare Interpretation / Alternativen sowie Sprachfestlegung (DE / EN)
    """)
        st.info("""🎯
    **Kernergebnis**:  
    Mehrstufige **Kontextintegration** unterstützt insbesondere **SQL-Unerfahrene**, während erweiterte **Assistenzfunktionen** gezielt Mehrwert für **erfahrenere Nutzende** bieten. Eine adaptive Steuerung der Informationsdichte und Sprachwahl ermöglicht die gezielte **Anpassung an unterschiedliche Nutzenden-Typen**                                       

    """)
        
# --------------------------------------------------
# Roadmap & Enterprise-Readiness
# --------------------------------------------------
with st.expander("🚀 Weiterentwicklungsperspektiven"):
    st.markdown("""
    Der aktuelle Prototyp verdeutlicht bereits das Potenzial natürlichsprachlicher Datenanalyse. Für einen **produktiven Einsatz** im Unternehmenskontext bestehen jedoch **noch mehrere Limitationen**, die durch **gezielte Weiterentwicklungen** adressiert werden können.""")

    st.divider()

    # Punkt 1: Integration & Self-Service
    st.markdown("#### **Erweiterte Datenanbindung (Self-Service)**")
    st.markdown("""
    **Limitation:**  
                In der im Rahmen der Masterarbeit entwickelten Version können **nur bereits integrierte Datenbanken** analysiert werden. Neue Datenquellen müssen zunächst technisch angebunden werden, bevor sie mit dem System genutzt werden können.   

    **Mögliche Erweiterung:**  
    - Uploads von **CSV-Exporten** anderer relationaler Datenbanken  
    - automatische Vorhersage von **Primär- und Fremdschlüsseln**
    - Generierung einer **DuckDB-Instanz** aus hochgeladenen CSV-Dateien  
    - automatische Erstellung eines **ER-Diagramms** zur strukturellen Orientierung  
                
    *Diese Erweiterung wurde bereits prototypisch umgesetzt, ist jedoch nicht Bestandteil der öffentlich zugänglichen Demonstration.*
    """)

    st.divider()

    # Punkt 2: Datenkomplexität
    st.markdown("#### **Skalierung der Knowledge-Base**")
    st.markdown("""
    **Limitation:**  
                Die Entwicklung und Optimierung des Systems basiert derzeit auf den **Spider- und SparC-Datensätze**. Diese bilden zwar typische Text-to-SQL-Probleme ab, repräsentieren jedoch nur begrenzt die Komplexität realer Unternehmensdaten.    
    
    **Mögliche Erweiterung:**
    - **Integration moderner Benchmarks** wie BIRD und Spider 2.0, um komplexere SQL-Strukturen, größere Schemata und realistischere Fragestellungen abzubilden  
    - **Erweiterung um domänenspezifische Beispiele**, etwa organisationsinterne Frage-SQL-Paare, um die Wissensbasis stärker an reale Analyseanforderungen anzupassen  
    - **Einführung von Workspaces**, ähnlich dem Konzept von Uber QueryGPT, um Wissen und Beispiele thematisch nach Datenbereichen zu strukturieren              
    """)

    st.divider()

    # Punkt 2.5: Ansatzverständnis
    st.markdown("#### **Schemaverständnis bei Join-Operationen**")
    st.markdown("""
    **Limitation:**  
                Die SQL-Generierung basiert auf Tabellen- und Spaltenstrukturen, berücksichtigt jedoch nicht explizit den **Modellierungsansatz** (z.B. Sternschema, Data Vault, etc.). Dadurch können bei komplexeren Schemata ungeeignete **Join-Bedingungen** entstehen, da ansatzabhängige **Best-Practices** nicht korrekt eingehalten werden, was zu redundanten Ergebnissen oder verfälschten **Aggregationen** führen kann.  
  
    **Mögliche Erweiterung:**  
    - **Automatische Klassifikation** des Modellierungsansatzes bei der Quelleneinbindung  
    - **Einschränkung und Steuerung** von Join-Pfaden basierend auf Schlüsselbeziehungen und dem Modellierungsansatz  
    - Nutzung **zusätzlicher Metadaten** zur Unterstützung der Abfragegenerierung  
    """)

    st.divider()

    # Punkt 3: Modellkapazität
    st.markdown("#### **Sprachmodellkapazität**")
    st.markdown("""
**Limitation:**  
Die aktuelle Implementierung basiert auf **GPT-4o mini**, einem vergleichsweise kompakten und kosteneffizienten Sprachmodell. Bei komplexeren Datenbankschemata oder anspruchsvolleren SQL-Strukturen kann die Generierung dadurch teilweise an Stabilität verlieren.

**Mögliche Erweiterung:**  
Eine mögliche Weiterentwicklung besteht darin, die bestehende Systemarchitektur auch mit **leistungsfähigeren oder kontextstärkeren Sprachmodellen** zu evaluieren. Dadurch ließe sich untersuchen, inwieweit höhere Modellkapazität die SQL-Generierung bei komplexeren Datenstrukturen verbessert und wie sich dies auf die implementierten RAG-Mechanismen auswirkt.
""")

    st.divider()

    # Punkt 4: Validierung
    st.markdown("#### **Evaluation & Nutzungsstudien**")
    st.markdown("""
**Limitation:**  
Die praktische Evaluation des Prototyps basiert auf einer explorativen Fallstudie mit **begrenzter Stichprobengröße** sowie einer **relativ kleinen Anzahl vorstrukturierter Analyseaufgaben**. Dadurch lassen sich erste Nutzungsmuster und Unterschiede zwischen den Systemstufen beobachten, jedoch nur eingeschränkt verallgemeinern.

**Mögliche Erweiterung:**  
Zukünftige Untersuchungen könnten die Systemvalidierung durch **größere Stichproben**, **standardisierte Aufgabenformate** sowie **längere Nutzungszeiträume** erweitern. Ergänzend wären **Real-World-Szenarien mit komplexeren Datenstrukturen** denkbar, um das Verhalten des Systems unter realistischen Analysebedingungen weiter zu untersuchen.
""")

    st.divider()

    # Punkt 5: Governance & Betrieb
    st.markdown("#### **Produktivsetzung & Systeminfrastruktur**")
    st.markdown("""
    **Limitation:**  
                Das System wurde als **Forschungsprototyp** entwickelt und ist derzeit als Einzelinstanz konzipiert. Aspekte wie Mehrnutzerbetrieb, Zugriffskontrollen oder organisatorische Governance-Mechanismen wurden im Rahmen der Implementierung nicht vollständig berücksichtigt.  

    **Mögliche Erweiterung:**  
    Für einen produktiven Einsatz wären **zusätzliche Infrastruktur- und Governance-Komponenten** erforderlich, darunter beispielsweise:  
    - rollenbasierte Zugriffskontrolle und Mandantenfähigkeit  
    - Mechanismen zur Datenisolierung und Zugriffsbeschränkung  
    - Monitoring und Logging generierter Abfragen  
    - Unterstützung für parallele Mehrnutzeranfragen      
    """)

#---------------------------------------------------
# Electricity & Climate Mart
#---------------------------------------------------
with st.expander("🗄️ Demonstrationsdatensatz: Renewables-Climate Mart", expanded=True):
    st.markdown("""
    Zur Demonstration des NLIDBs wurde ein **Data Mart** entwickelt, der die **Stromerzeugung eines erneuerbaren Energieportfolios** modelliert. Das Portfolio basiert auf den im **Geschäftsbericht** eines deutschen **Energieversorgers** ausgewiesenen Tochter- und Beteiligungsgesellschaften sowie zugehörigen Erzeugungsanlagen. Für die öffentliche Präsentation wurden **Unternehmens- und Anlagennamen** unter dem fiktiven Konzernnamen „Electricville“ zusammengeführt, um zu verdeutlichen, dass die dargestellten Erzeugungsmengen auf einem Modell basieren und nicht den tatsächlichen Erzeugungswerten der Anlagen entsprechen. 

    Die Datenbasis vereint öffentlich verfügbare Informationen aus drei Quellen:

    - **Marktstammdatenregister (MaStR)** – Stammdaten zu Erzeugungsanlagen, installierter Leistung, Inbetriebnahmedaten und Betreiberstrukturen
    - **SMARD** – historische Stromerzeugungsdaten der deutschen Übertragungsnetzbetreiber (Transmission System Operators, TSOs) für verschiedene Energieträger und Netzregionen
    - **Open-Meteo** – regionale Wetterdaten wie Lufttemperatur, Luftdruck, Windgeschwindigkeit und solare Einstrahlung

    Die Daten wurden extrahiert, harmonisiert und in einem **relationalen Snowflake-Schema** zusammengeführt. Auf Basis der historischen Stromerzeugung in den jeweiligen TSO-Netzregionen wurde die **tägliche Erzeugungsmengen einzelner Anlagen** in Kombination mit den **installierten Kapazitäten** sowie **Inbetriebnahmedaten** modelliert. Zusätzlich wurden meteorologische Kennzahlen wie **Windleistungsdichte** und **solare Einstrahlung** berechnet, um klimatische Einflussfaktoren analysierbar zu machen.
    """)

    st.info("""🎯
    **Kernidee**:  
    Der Data Mart verknüpft **Konzernstrukturen**, **Anlagenstammdaten**, **historische Erzeugungsprofile** und **Wetterindikatoren** auf Asset-Ebene. Dadurch ermöglicht das System Analysen zur **Asset-Performance**, **Portfolioentwicklung**, **regionalen Erzeugungsverteilung** sowie zum Einfluss von **Wetterbedingungen** auf die Stromproduktion.
    """)

    st.divider()
    
    st.markdown("""
    #### Anwendungsbeispiele  
    Im Folgenden werden exemplarische Einsatzszenarien des NLIDB vorgestellt. Für jeden Anwendungsfall werden Anfrage, Konfiguration und Ergebnis dokumentiert, sodass die Analysen nachvollzogen und bei Bedarf reproduziert werden können. Die Beispiele umfassen sowohl **einstufige** als auch **mehrstufige Analysen**.
    """)
    st.info("""
    ℹ️ **Hinweis**:  
    Die Beispiele wurden mehrfach validiert und entsprechen den Antworten in den meisten Fällen. Aufgrund der **nichtdeterministischen** Natur von Sprachmodellen können einzelne Antworten allerdings von den dargestellten Ergebnissen abweichen.
    """)

    tab1, tab2 = st.tabs(["Einstufige Analyse", "Mehrstufige Analyse"])

    with tab1:
        st.markdown("#### **Überblick: Generierungskapazitäten & Standorte**")
        st.markdown("**Fokus:** Geografische Analyse der installierten Kapazitäten und Standortverteilung nach Energieträgern und Betreibern.")
        
        # Der Prompt als zentrales Element
        st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-left: 5px solid #007bff; border-radius: 5px; margin-bottom: 20px;">
        <b style="color: #555; font-size: 0.9rem;">🗨️ Anfrage:</b><br>
        <i style="font-size: 1.0rem;">Map the generation capacity across Germany. Summarize the portfolio by energy source, operator and city. Ensure TSO regions, GPS coordinates and asset_counts are included for regional clustering.</i>
    </div>
    """, unsafe_allow_html=True)
        
        st.markdown("")

        st.markdown("""
    **Ablauf:** Die obige Anfrage wurde vom NLIDB in eine SQL-Abfrage übersetzt. Mithilfe des integrierten **Data Visualizers** (Konfiguration s.u.) wurde im nächsten Schritt aus den extrahierten Daten die folgende Visualisierung generiert:
    """)
        
        example1_df = pd.read_csv("assets/beispiel1.csv", index_col=0)

        fig = render_portfolio_map(example1_df)
        st.plotly_chart(fig, key=id(fig))
        st.caption("Hinweis: Für eine bessere Betrachtung lässt sich das Diagramm durch die rechte Oberleiste rein- & rauszoomen sowie im Vollbild öffnen.")
        st.markdown("""
                    <div style="background-color: #FFFFE0; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    💡 <b>Insight:</b><br>  
                    Die <b>Erzeugungsanlagen</b> des Electricville-Konzerns bilden <b>klare regionale Cluster</b> innerhalb Deutschlands. Insbesondere die größten <b>installierten Kapazitäten</b> entfallen auf <b>Windkraftanlagen in Norddeutschland</b>, während <b>Biomasse- und Solaranlagen</b> das Portfolio durch eine breitere geografische Verteilung ergänzen.
        </div>
        """, unsafe_allow_html=True)
        #st.divider()    
        #col_left, col_right = st.columns(2)
        #with col_left:
        with st.expander("📝 Details & Implementation"):
                t_sql, t_data, t_conf = st.tabs(["SQL Code", "Data", "Visualizer Config"])
                with t_sql:
                    sql_query_string = """
SELECT
  dim_energy_source_h.energy_source_name AS energy_source_name,
  dim_company_h.company_name AS company_name,
  dim_area_h.city AS city,
  dim_area_h.tso_region AS tso_region,
  dim_area_h.latitude AS latitude,
  dim_area_h.longitude AS longitude,
  COUNT(dim_asset.asset_id) AS asset_count,
  SUM(dim_asset.generation_capacity_mw) AS total_generation_capacity_mw
FROM dim_asset
JOIN dim_company_h
  ON dim_asset.company_id = dim_company_h.company_id
JOIN dim_area_h
  ON dim_asset.area_id = dim_area_h.area_id
JOIN dim_energy_source_h
  ON dim_asset.energy_source_id = dim_energy_source_h.energy_source_id
GROUP BY
  dim_energy_source_h.energy_source_name,
  dim_company_h.company_name,
  dim_area_h.city,
  dim_area_h.tso_region,
  dim_area_h.latitude,
  dim_area_h.longitude
ORDER BY
  total_generation_capacity_mw DESC,
  asset_count DESC,
  energy_source_name,
  company_name,
  city;
"""
                    st.code(sql_query_string, language="sql",wrap_lines=True)
            
        #with col_right:
            # Die Tabelle "verstecken" wir in einem Expander
                with t_data:
                    st.caption("Folgende Tabelle wurde vom NLIDB aus dem Electricity-Climate Mart extrahiert.")
                    st.dataframe(example1_df, use_container_width=True)

                with t_conf:
                    st.caption("Die finale Visualisierung nutzte folgende Logik:")
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.markdown("""
                                    ###### Nummeric Column  
                                    "total_generation_capacity_mw"
                                    """) 
                    with c2:
                        st.markdown("""
                                    ###### Additional Columns   
                                    "energy_source_name", "company_name", "city", "tso_region", "latitude", "longitude", "asset_count"
                                    """)
                        
                    with c3:
                        st.markdown("""
                                    ###### Details  
                                    "map: carto-positron; color: energy_source_name (wind: light purple, biomass: green, solar: orange, hydro: red; hover_name: company_name + " | " + city; hover_data: tso_region, total_generation_capacity_mw.round(2), asset_count; size: generation_capacity_mw; zoom=5; height= 800; size_max=40; change energy_source_name to 'Energy Source' "
                                    """)
                
                
    with tab2:
        st.markdown("#### **Deep Dive: Ursachenanalyse des Erzeugungswachstums**")
        st.markdown("**Ziel:** Analyse der **Ursachen für Veränderungen** der Stromerzeugung erneuerbarer Energieträger zwischen **2024 und 2025**. Die Untersuchung erfolgt schrittweise von der Identifikation von **Wachstumsmustern** über die Analyse möglicher **Einflussfaktoren** bis hin zur **quantitativen Bewertung** ihrer Zusammenhänge.")
        st.divider()

        # --- HAUPT-TABS (Option 2: Strukturiert nach Frage) ---
        step1_tab, step2_tab, step3_tab = st.tabs([ 
            "Schritt 1: Growth-Comparision", 
            "Schritt 2: Cause-Identification", 
            "Schritt 3: Correlation Coefficient"
        ])
        

        # ==========================================
        # SCHRITT 1: SOURCE BREAKDOWN
        # ==========================================
        with step1_tab:
            st.markdown("**Fokus:** Vergleich der Erzeugungsentwicklung erneuerbarer Energieträger zwischen 2024 und 2025, um Unterschiede in absolutem und relativem Wachstum zu identifizieren.")

            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 15px; border-left: 5px solid #007bff; border-radius: 5px; margin-bottom: 20px;">
                <b style="color: #555; font-size: 0.9rem;">🗨️ Anfrage 1:</b><br>
                <i>Compare the monthly renewable energy generation between the iso_years 2024 and 2025 on individual energy source level. Display the progress for both years and calculate the year-over-year growth in both absolute (MWh) and percentage terms. Add a 'Total Renewables' summary row as a baseline comparison.</i>
            </div>
            """, unsafe_allow_html=True)

            example3_df = pd.read_csv("assets/beispiel3.csv", index_col=0)

            fig3 = create_energy_source_breakdown_plot(example3_df)
            st.plotly_chart(fig3, key=id(fig3))

            st.markdown(f"""
                <div style="background-color: #FFFFE0; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <b>💡 Insight:</b><br>
                    <b>Windenergie</b> prägt die Gesamtentwicklung und weist zugleich die höchste Volatilität auf, <b>Biomasse</b> liefert stabile Beiträge und <b>Solarenergie</b> erzielt die stärksten prozentualen Wachstumsraten.
                                        </div>
                """, unsafe_allow_html=True)

            with st.expander("📝 Details & Implementation"):
                t_sql, t_data, t_conf = st.tabs(["SQL Code", "Data", "Visualizer Config"])
                with t_sql:
                    st.code("""-- SQL 1: Growth-Comparision
WITH monthly_gen AS (
  SELECT
    dim_date.year_iso AS year_iso,
    dim_date.month AS month,
    dim_energy_source_h.energy_source_name AS energy_source_name,
    SUM(fact_generation.generation_mwh) AS generation_mwh
  FROM fact_generation
  JOIN dim_date
    ON fact_generation.date_id = dim_date.date_id
  JOIN dim_asset
    ON fact_generation.asset_id = dim_asset.asset_id
  JOIN dim_energy_source_h
    ON dim_asset.energy_source_id = dim_energy_source_h.energy_source_id
  WHERE dim_date.year_iso IN (2024, 2025)
    AND dim_energy_source_h.energy_source_group = 'Renewable'
  GROUP BY dim_date.year_iso, dim_date.month, dim_energy_source_h.energy_source_name
),
pivoted AS (
  SELECT
    month,
    energy_source_name,
    SUM(CASE WHEN year_iso = 2024 THEN generation_mwh ELSE 0 END) AS generation_mwh_2024,
    SUM(CASE WHEN year_iso = 2025 THEN generation_mwh ELSE 0 END) AS generation_mwh_2025
  FROM monthly_gen
  GROUP BY month, energy_source_name
),
total_renewables AS (
  SELECT
    month,
    'Total Renewables' AS energy_source_name,
    SUM(generation_mwh_2024) AS generation_mwh_2024,
    SUM(generation_mwh_2025) AS generation_mwh_2025
  FROM pivoted
  GROUP BY month
),
combined AS (
  SELECT
    month,
    energy_source_name,
    generation_mwh_2024,
    generation_mwh_2025,
    (generation_mwh_2025 - generation_mwh_2024) AS yoy_growth_mwh,
    CASE
      WHEN generation_mwh_2024 = 0 THEN NULL
      ELSE ((generation_mwh_2025 - generation_mwh_2024) * 100.0 / generation_mwh_2024)
    END AS yoy_growth_pct
  FROM pivoted
  UNION ALL
  SELECT
    month,
    energy_source_name,
    generation_mwh_2024,
    generation_mwh_2025,
    (generation_mwh_2025 - generation_mwh_2024) AS yoy_growth_mwh,
    CASE
      WHEN generation_mwh_2024 = 0 THEN NULL
      ELSE ((generation_mwh_2025 - generation_mwh_2024) * 100.0 / generation_mwh_2024)
    END AS yoy_growth_pct
  FROM total_renewables
)
SELECT
  combined.month,
  combined.energy_source_name,
  combined.generation_mwh_2024,
  combined.generation_mwh_2025,
  combined.yoy_growth_mwh,
  combined.yoy_growth_pct
FROM combined
ORDER BY combined.month, CASE WHEN combined.energy_source_name = 'Total Renewables' THEN 0 ELSE 1 END, combined.energy_source_name;
""", language="sql", wrap_lines=True)
                with t_data:
                    st.dataframe(example3_df)
                    st.caption("Extrahierter DataFrame für Schritt 1")
                with t_conf:
                    st.caption("Die finale Visualisierung nutzte folgende Logik:") 
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.markdown("""
                                    ###### Nummeric Column  
                                    "yoy_growth_mwh"
                                    """) 
                    with c2:
                        st.markdown("""
                                    ###### Additional Columns   
                                    "month", "energy_source_name", "yoy_growth_pct"
                                    """)
                        
                    with c3:
                        st.markdown("""
                                    ###### Details  
                                    "two charts ((1) yoy_growth_mwh, (2) yoy_growth_pct)); x-scale: month; total renewables as line, energy_source as bar (wind: mediumpurple, biomass: green, solar: orange, hydro: red)"
                                    """)

        # ==========================================
        # SCHRITT 2: WIND DIAGNOSTIC
        # ==========================================
        with step2_tab:
            st.markdown("**Fokus:** Untersuchung, ob die beobachteten Veränderungen bei Windenergie primär durch Kapazitätsausbau oder durch veränderte Wetterbedingungen erklärt werden können.")

            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 15px; border-left: 5px solid #007bff; border-radius: 5px; margin-bottom: 20px;">
                <b style="color: #555; font-size: 0.9rem;">🗨️ Anfrage 2:</b><br>
                <i>Focus on wind energy only. Next to absolute growth provide the year-over-year difference in a) total installed wind asset capacity (MW) for each month and b) average wind_power_density for the areas with wind assets.</i>
            </div>
            """, unsafe_allow_html=True)

            example4_df = pd.read_csv("assets/beispiel4.csv", index_col=0)

            fig4 = create_monthly_metrics_plot(example4_df)
            st.plotly_chart(fig4, key=id(fig4))

            st.markdown(f"""
                <div style="background-color: #FFFFE0; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <b>💡 Insight:</b><br>
                        <b>Kapazitätsänderungen</b> verlaufen vergleichsweise konstant, während die <b>Windleistungsdichte</b> starke Schwankungen aufweist. Die Entwicklung der <b>Windenergieerzeugung</b> scheint daher stärker durch Wetterbedingungen als durch den Ausbau installierter Leistung beeinflusst zu werden.
                </div>
                """, unsafe_allow_html=True)

            with st.expander("📝 Details & Implementation"):
                t_sql, t_data, t_conf = st.tabs(["SQL Code", "Data", "Visualizer Config"])
                with t_sql:
                    st.code("""-- SQL 2: Cause-Identification
WITH monthly_wind_generation AS (
    SELECT
        d.month,
        d.year_iso,
        SUM(fg.generation_mwh) AS generation_mwh
    FROM fact_generation_daily fg
    JOIN dim_date d ON fg.date_id = d.date_id
    JOIN dim_asset a ON fg.asset_id = a.asset_id
    JOIN dim_energy_source_h es ON a.energy_source_id = es.energy_source_id
    WHERE es.energy_source_name = 'Wind'
      AND d.year_iso IN (2024, 2025)
    GROUP BY d.month, d.year_iso
),
monthly_wind_capacity AS (
    SELECT
        d.month,
        d.year_iso,
        (
            SELECT SUM(a2.generation_capacity_mw)
            FROM dim_asset a2
            JOIN dim_date d_comm ON a2.commissioning_date_id = d_comm.date_id
            WHERE (d_comm.year_iso < d.year_iso OR (d_comm.year_iso = d.year_iso AND d_comm.month <= d.month))
              AND a2.energy_source_id = es.energy_source_id
        ) AS installed_capacity_mw
    FROM dim_date d
    CROSS JOIN (
        SELECT DISTINCT es.energy_source_id
        FROM dim_energy_source_h es
        WHERE es.energy_source_name = 'Wind'
    ) es
    WHERE d.year_iso IN (2024, 2025)
    GROUP BY d.month, d.year_iso, es.energy_source_id
),
monthly_wind_weather AS (
    SELECT
        d.month,
        d.year_iso,
        AVG(fw.avg_wind_power_density_w_per_m2) AS avg_wind_power_density_w_per_m2
    FROM fact_weather_daily fw
    JOIN dim_date d ON fw.date_id = d.date_id
    WHERE d.year_iso IN (2024, 2025)
      AND fw.area_id IN (
          SELECT DISTINCT a.area_id
          FROM dim_asset a
          JOIN dim_energy_source_h es ON a.energy_source_id = es.energy_source_id
          WHERE es.energy_source_name = 'Wind'
      )
    GROUP BY d.month, d.year_iso
),
pivoted AS (
    SELECT
        g.month,
        g.generation_mwh AS generation_mwh_2024,
        g2.generation_mwh AS generation_mwh_2025,
        c.installed_capacity_mw AS installed_capacity_mw_2024,
        c2.installed_capacity_mw AS installed_capacity_mw_2025,
        w.avg_wind_power_density_w_per_m2 AS avg_wind_power_density_w_per_m2_2024,
        w2.avg_wind_power_density_w_per_m2 AS avg_wind_power_density_w_per_m2_2025
    FROM monthly_wind_generation g
    LEFT JOIN monthly_wind_generation g2
        ON g.month = g2.month
       AND g2.year_iso = 2025
    LEFT JOIN monthly_wind_capacity c
        ON g.month = c.month
       AND c.year_iso = 2024
    LEFT JOIN monthly_wind_capacity c2
        ON g.month = c2.month
       AND c2.year_iso = 2025
    LEFT JOIN monthly_wind_weather w
        ON g.month = w.month
       AND w.year_iso = 2024
    LEFT JOIN monthly_wind_weather w2
        ON g.month = w2.month
       AND w2.year_iso = 2025
    WHERE g.year_iso = 2024
)
SELECT
    month,
    generation_mwh_2024,
    generation_mwh_2025,
    generation_mwh_2025 - generation_mwh_2024 AS yoy_growth_mwh,
    installed_capacity_mw_2024,
    installed_capacity_mw_2025,
    installed_capacity_mw_2025 - installed_capacity_mw_2024 AS yoy_diff_installed_capacity_mw,
    avg_wind_power_density_w_per_m2_2024,
    avg_wind_power_density_w_per_m2_2025,
    avg_wind_power_density_w_per_m2_2025 - avg_wind_power_density_w_per_m2_2024 AS yoy_diff_avg_wind_power_density_w_per_m2
FROM pivoted
ORDER BY month;
""", language="sql", wrap_lines=True)
                with t_data:
                    st.dataframe(example4_df)
                    st.caption("Extrahierter DataFrame für Schritt 2")
                with t_conf:
                    st.caption("Die finale Visualisierung nutzte folgende Logik:")
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.markdown("""
                                    ###### Nummeric Column  
                                    "month"
                                    """) 
                    with c2:
                        st.markdown("""
                                    ###### Additional Columns   
                                    "yoy_growth_mwh", "yoy_diff_installed_capacity_mw", "yoy_diff_avg_wind_power_density_w_per_m2"
                                    """)
                        
                    with c3:
                        st.markdown("""
                                    ###### Details  
                                    "3 line charts"
                                    """)

        # ==========================================
        # SCHRITT 3: SOLAR IMPACT
        # ==========================================
        with step3_tab:
            st.markdown("**Fokus:** Quantifizierung der Zusammenhänge zwischen Erzeugungswachstum, Kapazitätsänderungen und Wetterindikatoren zur Bewertung möglicher Einflussfaktoren.")

            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 15px; border-left: 5px solid #007bff; border-radius: 5px; margin-bottom: 20px;">
                <b style="color: #555; font-size: 0.9rem;">🗨️ Anfrage 3a:</b><br>
                <i>Save the last analysis as a CTE and calculate the total correlation between growth (MWh) and a) difference in installed capacity (MW) as well as b) difference in wind_power_density. Compare these to identify if a drop in growth was caused by a drop in capacity or wind_power_density.</i>
            </div>
            """, unsafe_allow_html=True)

            example5a_df = pd.read_csv("assets/beispiel5a.csv", index_col=0)
            st.dataframe(example5a_df, hide_index=True)

            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 15px; border-left: 5px solid #007bff; border-radius: 5px; margin-bottom: 20px;">
                <b style="color: #555; font-size: 0.9rem;">🗨️ Anfrage 3b:</b><br>
                <i>Repeat the same correlation calculation for solar energy. Use total solar_irradiation instead of average wind_power_density.</i>
            </div>
            """, unsafe_allow_html=True)

            example5b_df = pd.read_csv("assets/beispiel5b.csv", index_col=0)
            st.dataframe(example5b_df, hide_index=True)

            st.markdown(f"""
                <div style="background-color: #FFFFE0; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <b>💡 Insight:</b><br>
                        Die <b>Windenergieerzeugung</b> wird primär durch die <b>Windleistungsdichte</b> beeinflusst. Bei der <b>Solarenergie</b> tragen sowohl <b>Kapazitätsausbau</b> als auch <b>solare Einstrahlung</b> zum Erzeugungswachstum bei, wobei der Zusammenhang mit dem Kapazitätsausbau etwas stärker ausfällt.
                </div>
                """, unsafe_allow_html=True)

            with st.expander("📝 Details & Implementation"):
                t_sqla, t_sqlb = st.tabs(["SQL Code 3a", "SQL Code 3b"])
                with t_sqla:
                    st.code("""-- SQL 3a: Correlation Wind
WITH monthly_wind_generation AS (
    SELECT
        d.month,
        d.year_iso,
        SUM(fg.generation_mwh) AS generation_mwh
    FROM fact_generation_daily fg
    JOIN dim_date d ON fg.date_id = d.date_id
    JOIN dim_asset a ON fg.asset_id = a.asset_id
    JOIN dim_energy_source_h es ON a.energy_source_id = es.energy_source_id
    WHERE es.energy_source_name = 'Wind'
      AND d.year_iso IN (2024, 2025)
    GROUP BY d.month, d.year_iso
),
monthly_wind_capacity AS (
    SELECT
        d.month,
        d.year_iso,
        (
            SELECT SUM(a2.generation_capacity_mw)
            FROM dim_asset a2
            JOIN dim_date d_comm ON a2.commissioning_date_id = d_comm.date_id
            WHERE (d_comm.year_iso < d.year_iso OR (d_comm.year_iso = d.year_iso AND d_comm.month <= d.month))
              AND a2.energy_source_id = es.energy_source_id
        ) AS installed_capacity_mw
    FROM dim_date d
    CROSS JOIN (
        SELECT DISTINCT es.energy_source_id
        FROM dim_energy_source_h es
        WHERE es.energy_source_name = 'Wind'
    ) es
    WHERE d.year_iso IN (2024, 2025)
    GROUP BY d.month, d.year_iso, es.energy_source_id
),
monthly_wind_weather AS (
    SELECT
        d.month,
        d.year_iso,
        AVG(fw.avg_wind_power_density_w_per_m2) AS avg_wind_power_density_w_per_m2
    FROM fact_weather_daily fw
    JOIN dim_date d ON fw.date_id = d.date_id
    WHERE d.year_iso IN (2024, 2025)
      AND fw.area_id IN (
          SELECT DISTINCT a.area_id
          FROM dim_asset a
          JOIN dim_energy_source_h es ON a.energy_source_id = es.energy_source_id
          WHERE es.energy_source_name = 'Wind'
      )
    GROUP BY d.month, d.year_iso
),
paired AS (
    SELECT
        g24.month,
        g25.generation_mwh - g24.generation_mwh AS growth_mwh,
        c25.installed_capacity_mw - c24.installed_capacity_mw AS diff_installed_capacity_mw,
        w25.avg_wind_power_density_w_per_m2 - w24.avg_wind_power_density_w_per_m2 AS diff_wind_power_density
    FROM monthly_wind_generation g24
    JOIN monthly_wind_generation g25
        ON g24.month = g25.month
       AND g24.year_iso = 2024
       AND g25.year_iso = 2025
    JOIN monthly_wind_capacity c24
        ON g24.month = c24.month
       AND c24.year_iso = 2024
    JOIN monthly_wind_capacity c25
        ON g24.month = c25.month
       AND c25.year_iso = 2025
    JOIN monthly_wind_weather w24
        ON g24.month = w24.month
       AND w24.year_iso = 2024
    JOIN monthly_wind_weather w25
        ON g24.month = w25.month
       AND w25.year_iso = 2025
)
SELECT
    corr(growth_mwh, diff_installed_capacity_mw) AS correlation_growth_capacity,
    corr(growth_mwh, diff_wind_power_density) AS correlation_growth_wind_power_density,
    CASE
        WHEN abs(corr(growth_mwh, diff_installed_capacity_mw)) > abs(corr(growth_mwh, diff_wind_power_density))
            THEN 'Capacity difference is more associated with growth changes'
        WHEN abs(corr(growth_mwh, diff_installed_capacity_mw)) < abs(corr(growth_mwh, diff_wind_power_density))
            THEN 'Wind power density difference is more associated with growth changes'
        ELSE 'Both factors are equally associated with growth changes'
    END AS comparison
FROM paired;
""", language="sql", wrap_lines=True)
                with t_sqlb:
                    st.code("""-- SQL 3b: Correlation Solar
WITH monthly_solar_generation AS (
    SELECT
        d.month,
        d.year_iso,
        SUM(fg.generation_mwh) AS generation_mwh
    FROM fact_generation_daily fg
    JOIN dim_date d ON fg.date_id = d.date_id
    JOIN dim_asset a ON fg.asset_id = a.asset_id
    JOIN dim_energy_source_h es ON a.energy_source_id = es.energy_source_id
    WHERE es.energy_source_name = 'Solar'
      AND d.year_iso IN (2024, 2025)
    GROUP BY d.month, d.year_iso
),
monthly_solar_capacity AS (
    SELECT
        d.month,
        d.year_iso,
        (
            SELECT SUM(a2.generation_capacity_mw)
            FROM dim_asset a2
            JOIN dim_date d_comm ON a2.commissioning_date_id = d_comm.date_id
            WHERE (d_comm.year_iso < d.year_iso OR (d_comm.year_iso = d.year_iso AND d_comm.month <= d.month))
              AND a2.energy_source_id = es.energy_source_id
        ) AS installed_capacity_mw
    FROM dim_date d
    CROSS JOIN (
        SELECT DISTINCT es.energy_source_id
        FROM dim_energy_source_h es
        WHERE es.energy_source_name = 'Solar'
    ) es
    WHERE d.year_iso IN (2024, 2025)
    GROUP BY d.month, d.year_iso, es.energy_source_id
),
monthly_solar_weather AS (
    SELECT
        d.month,
        d.year_iso,
        AVG(fw.total_solar_irradiation_kwh_per_m2) AS total_solar_irradiation_kwh_per_m2
    FROM fact_weather_daily fw
    JOIN dim_date d ON fw.date_id = d.date_id
    WHERE d.year_iso IN (2024, 2025)
      AND fw.area_id IN (
          SELECT DISTINCT a.area_id
          FROM dim_asset a
          JOIN dim_energy_source_h es ON a.energy_source_id = es.energy_source_id
          WHERE es.energy_source_name = 'Solar'
      )
    GROUP BY d.month, d.year_iso
),
paired AS (
    SELECT
        g24.month,
        g25.generation_mwh - g24.generation_mwh AS growth_mwh,
        c25.installed_capacity_mw - c24.installed_capacity_mw AS diff_installed_capacity_mw,
        w25.total_solar_irradiation_kwh_per_m2 - w24.total_solar_irradiation_kwh_per_m2 AS diff_total_solar_irradiation
    FROM monthly_solar_generation g24
    JOIN monthly_solar_generation g25
        ON g24.month = g25.month
       AND g24.year_iso = 2024
       AND g25.year_iso = 2025
    JOIN monthly_solar_capacity c24
        ON g24.month = c24.month
       AND c24.year_iso = 2024
    JOIN monthly_solar_capacity c25
        ON g24.month = c25.month
       AND c25.year_iso = 2025
    JOIN monthly_solar_weather w24
        ON g24.month = w24.month
       AND w24.year_iso = 2024
    JOIN monthly_solar_weather w25
        ON g24.month = w25.month
       AND w25.year_iso = 2025
)
SELECT
    corr(growth_mwh, diff_installed_capacity_mw) AS correlation_growth_capacity,
    corr(growth_mwh, diff_total_solar_irradiation) AS correlation_growth_total_solar_irradiation,
    CASE
        WHEN abs(corr(growth_mwh, diff_installed_capacity_mw)) > abs(corr(growth_mwh, diff_total_solar_irradiation))
            THEN 'Capacity difference is more associated with growth changes'
        WHEN abs(corr(growth_mwh, diff_installed_capacity_mw)) < abs(corr(growth_mwh, diff_total_solar_irradiation))
            THEN 'Solar irradiation difference is more associated with growth changes'
        ELSE 'Both factors are equally associated with growth changes'
    END AS comparison
FROM paired;
""", language="sql", wrap_lines=True)