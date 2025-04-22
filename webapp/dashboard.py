import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from sqlalchemy import create_engine
import os

# Datadog tracing
from ddtrace import patch_all, tracer
patch_all()
tracer.set_tags({"service.name": "gadgetgrove-analytics-dashboard"})


# Database connection
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "events")

# Create SQLAlchemy engine
engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport",
                "content": "width=device-width, initial-scale=1"}],
)

app.title = "GadgetGrove Analytics Dashboard"

# Define the layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("GadgetGrove Analytics Dashboard",
                    className="text-primary my-4"),
            html.P(
                "E-commerce performance metrics and user behavior analysis", className="lead")
        ], width=12)
    ]),

    # Time Range Selector
    dbc.Row([
        dbc.Col([
            html.Label("Select Date Range:"),
            dcc.DatePickerRange(
                id='date-range',
                start_date_placeholder_text="Start Date",
                end_date_placeholder_text="End Date",
                calendar_orientation='horizontal',
                className="mb-4"
            )
        ], width=12)
    ]),

    # KPI Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Sessions",
                            className="card-title text-center"),
                    html.H2(id="total-sessions",
                            className="card-text text-center text-primary")
                ])
            ], className="mb-4 shadow-sm")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Conversion Rate",
                            className="card-title text-center"),
                    html.H2(id="conversion-rate",
                            className="card-text text-center text-success")
                ])
            ], className="mb-4 shadow-sm")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Revenue", className="card-title text-center"),
                    html.H2(id="total-revenue",
                            className="card-text text-center text-info")
                ])
            ], className="mb-4 shadow-sm")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Avg Order Value",
                            className="card-title text-center"),
                    html.H2(id="avg-order-value",
                            className="card-text text-center text-warning")
                ])
            ], className="mb-4 shadow-sm")
        ], md=3)
    ]),

    # Charts - Row 1
    dbc.Row([
        # Daily Traffic & Revenue
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Daily Traffic & Revenue"),
                dbc.CardBody([
                    dcc.Graph(id="daily-metrics-chart")
                ])
            ], className="mb-4 shadow-sm")
        ], md=8),
        # Session Outcomes
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Session Outcomes"),
                dbc.CardBody([
                    dcc.Graph(id="session-outcomes-chart")
                ])
            ], className="mb-4 shadow-sm")
        ], md=4)
    ]),

    # Charts - Row 2
    dbc.Row([
        # Conversion Funnel
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Conversion Funnel"),
                dbc.CardBody([
                    dcc.Graph(id="funnel-chart")
                ])
            ], className="mb-4 shadow-sm")
        ], md=6),
        # Products Performance
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Top Products by Revenue"),
                dbc.CardBody([
                    dcc.Graph(id="products-chart")
                ])
            ], className="mb-4 shadow-sm")
        ], md=6)
    ]),

    # Charts - Row 3
    dbc.Row([
        # Cohort Retention Matrix
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Cohort Retention Analysis"),
                dbc.CardBody([
                    dcc.Graph(id="cohort-retention-chart")
                ])
            ], className="mb-4 shadow-sm")
        ], width=12)
    ]),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("GadgetGrove Analytics Dashboard - Data refreshes every 10 minutes",
                   className="text-muted text-center")
        ], width=12)
    ])
], fluid=True)

# Callbacks for updating the dashboard


@callback(
    [Output("total-sessions", "children"),
     Output("conversion-rate", "children"),
     Output("total-revenue", "children"),
     Output("avg-order-value", "children")],
    [Input("date-range", "start_date"),
     Input("date-range", "end_date")]
)
def update_kpi_metrics(start_date, end_date):
    # Get daily metrics from the database
    query = """
    SELECT 
        SUM(total_sessions) AS total_sessions,
        SUM(purchase_sessions)::float / NULLIF(SUM(total_sessions), 0) AS conversion_rate,
        SUM(total_revenue) AS total_revenue,
        SUM(total_revenue) / NULLIF(SUM(purchase_sessions), 0) AS avg_order_value
    FROM analytics.daily_metrics
    """

    if start_date and end_date:
        query += f" WHERE event_date BETWEEN '{start_date}' AND '{end_date}'"

    try:
        df = pd.read_sql_query(query, engine)

        total_sessions = f"{int(df['total_sessions'].iloc[0]):,}" if not pd.isna(
            df['total_sessions'].iloc[0]) else "0"
        conversion_rate = f"{df['conversion_rate'].iloc[0]:.2%}" if not pd.isna(
            df['conversion_rate'].iloc[0]) else "0%"
        total_revenue = f"${df['total_revenue'].iloc[0]:,.2f}" if not pd.isna(
            df['total_revenue'].iloc[0]) else "$0.00"
        avg_order_value = f"${df['avg_order_value'].iloc[0]:,.2f}" if not pd.isna(
            df['avg_order_value'].iloc[0]) else "$0.00"

        return total_sessions, conversion_rate, total_revenue, avg_order_value
    except Exception as e:
        print(f"Error fetching KPI metrics: {e}")
        return "0", "0%", "$0.00", "$0.00"


@callback(
    Output("daily-metrics-chart", "figure"),
    [Input("date-range", "start_date"),
     Input("date-range", "end_date")]
)
def update_daily_metrics_chart(start_date, end_date):
    query = """
    SELECT 
        event_date,
        total_sessions,
        total_revenue
    FROM analytics.daily_metrics
    ORDER BY event_date
    """

    if start_date and end_date:
        query = query.replace(
            "ORDER BY", f"WHERE event_date BETWEEN '{start_date}' AND '{end_date}' ORDER BY")

    try:
        df = pd.read_sql_query(query, engine)

        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces
        fig.add_trace(
            go.Bar(
                x=df["event_date"],
                y=df["total_sessions"],
                name="Sessions",
                marker_color='rgb(55, 83, 109)'
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=df["event_date"],
                y=df["total_revenue"],
                name="Revenue",
                marker_color='rgb(26, 118, 255)',
                mode='lines+markers'
            ),
            secondary_y=True,
        )

        # Set y-axes titles
        fig.update_yaxes(title_text="Number of Sessions", secondary_y=False)
        fig.update_yaxes(title_text="Revenue ($)", secondary_y=True)

        fig.update_layout(
            xaxis_title="Date",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=20, r=20, t=40, b=20),
            height=400
        )

        return fig
    except Exception as e:
        print(f"Error generating daily metrics chart: {e}")
        return go.Figure()


@callback(
    Output("session-outcomes-chart", "figure"),
    [Input("date-range", "start_date"),
     Input("date-range", "end_date")]
)
def update_session_outcomes_chart(start_date, end_date):
    query = """
    SELECT 
        session_outcome,
        COUNT(*) as count
    FROM analytics.session_summary
    """

    if start_date and end_date:
        query += f" WHERE session_start BETWEEN '{start_date}' AND '{end_date}'"

    query += " GROUP BY session_outcome"

    try:
        df = pd.read_sql_query(query, engine)

        colors = {
            'purchase': '#28a745',
            'checkout_error': '#dc3545',
            'cart_abandonment': '#ffc107',
            'browse_only': '#17a2b8',
            'bounce': '#6c757d'
        }

        fig = px.pie(
            df,
            values='count',
            names='session_outcome',
            color='session_outcome',
            color_discrete_map=colors,
            hole=0.4
        )

        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20),
            height=350
        )

        return fig
    except Exception as e:
        print(f"Error generating session outcomes chart: {e}")
        return go.Figure()


@callback(
    Output("funnel-chart", "figure"),
    [Input("date-range", "start_date"),
     Input("date-range", "end_date")]
)
def update_funnel_chart(start_date, end_date):
    query = """
    SELECT 
        SUM(total_sessions) as total_sessions,
        SUM(browse_sessions) as browse_sessions,
        SUM(product_sessions) as product_sessions,
        SUM(cart_sessions) as cart_sessions,
        SUM(purchase_sessions) as purchase_sessions
    FROM analytics.funnel_analysis
    """

    if start_date and end_date:
        query += f" WHERE event_date BETWEEN '{start_date}' AND '{end_date}'"

    try:
        df = pd.read_sql_query(query, engine)

        stages = ['Sessions', 'Browse',
                  'Product View', 'Add to Cart', 'Purchase']
        values = [
            df['total_sessions'].iloc[0],
            df['browse_sessions'].iloc[0],
            df['product_sessions'].iloc[0],
            df['cart_sessions'].iloc[0],
            df['purchase_sessions'].iloc[0]
        ]

        # Calculate conversion percentages
        percentages = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                pct = values[i] / values[i-1] * 100
                percentages.append(f"{pct:.1f}%")
            else:
                percentages.append("0.0%")

        # Insert None at the beginning since there's no percentage for the first stage
        percentages.insert(0, None)

        # Create funnel chart
        fig = go.Figure(go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker={"color": ["#6c757d", "#17a2b8",
                              "#fd7e14", "#ffc107", "#28a745"]}
        ))

        # Add conversion rate annotations
        for i in range(1, len(stages)):
            fig.add_annotation(
                x=0.1,
                y=i-0.5,
                text=f"Conversion: {percentages[i]}",
                showarrow=False,
                xanchor="left"
            )

        fig.update_layout(
            margin=dict(l=100, r=20, t=20, b=20),
            height=400
        )

        return fig
    except Exception as e:
        print(f"Error generating funnel chart: {e}")
        return go.Figure()


@callback(
    Output("products-chart", "figure"),
    [Input("date-range", "start_date"),
     Input("date-range", "end_date")]
)
def update_products_chart(start_date, end_date):
    query = """
    SELECT 
        product_id,
        product_name,
        product_brand,
        views,
        adds_to_cart,
        purchases,
        total_revenue
    FROM analytics.product_performance
    ORDER BY total_revenue DESC
    LIMIT 10
    """

    try:
        df = pd.read_sql_query(query, engine)

        # Truncate long product names
        df['display_name'] = df['product_name'].str.slice(0, 25) + "..."
        df['display_name'] = df['display_name'].str.cat(
            df['product_brand'].astype(str), sep=' - ')

        fig = px.bar(
            df,
            y='display_name',
            x='total_revenue',
            orientation='h',
            color='total_revenue',
            color_continuous_scale=px.colors.sequential.Blues,
            text='purchases'
        )

        fig.update_traces(texttemplate='%{text} sold', textposition='outside')
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title="Revenue ($)",
            yaxis_title="",
            coloraxis_showscale=False,
            margin=dict(l=20, r=20, t=20, b=20),
            height=400
        )

        return fig
    except Exception as e:
        print(f"Error generating products chart: {e}")
        return go.Figure()


@callback(
    Output("cohort-retention-chart", "figure"),
    [Input("date-range", "start_date"),
     Input("date-range", "end_date")]
)
def update_cohort_retention_chart(start_date, end_date):
    query = """
    SELECT 
        cohort_date,
        weeks_since_first_visit,
        retention_rate
    FROM analytics.user_cohort_analysis
    WHERE weeks_since_first_visit <= 8
    ORDER BY cohort_date, weeks_since_first_visit
    """

    try:
        df = pd.read_sql_query(query, engine)

        # Convert to pivot table format for heatmap
        pivot_df = df.pivot(
            index='cohort_date',
            columns='weeks_since_first_visit',
            values='retention_rate'
        ).reset_index()

        # Convert to datetime and format cohort date
        pivot_df['cohort_date'] = pd.to_datetime(pivot_df['cohort_date'])
        pivot_df['cohort_str'] = pivot_df['cohort_date'].dt.strftime(
            '%Y-%m-%d')

        # Replace NaN with 0
        pivot_df = pivot_df.fillna(0)

        # Get column names for weeks
        week_cols = [
            col for col in pivot_df.columns if isinstance(col, (int, float))]

        # Create heatmap data
        z_data = pivot_df[week_cols].values
        x_data = [f"Week {int(col)}" for col in week_cols]
        y_data = pivot_df['cohort_str'].tolist()

        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=x_data,
            y=y_data,
            colorscale='Blues',
            text=[[f"{val*100:.1f}%" for val in row] for row in z_data],
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverinfo='text',
            hovertext=[[f"Cohort: {y}<br>Week: {x}<br>Retention: {val*100:.1f}%"
                        for val in row] for y, row in zip(y_data, z_data)]
        ))

        fig.update_layout(
            title="User Retention by Cohort (Weekly)",
            xaxis_title="Weeks Since First Visit",
            yaxis_title="Cohort (First Visit Date)",
            margin=dict(l=20, r=20, t=50, b=20),
            height=500
        )

        return fig
    except Exception as e:
        print(f"Error generating cohort retention chart: {e}")
        return go.Figure()


# Start the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
