import dash
from dash import dcc, html, Input, Output, ctx, ALL
import dash_bootstrap_components as dbc
import yfinance as yf
import requests
import json
from urllib.request import urlopen
import certifi
import ssl

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Stock Market Dashboard"

# API Key for Polygon
POLYGON_API_KEY = "8uK6hchgdm_LgpL8nUa_PQyQ9ZTYS_5Z"

# Create SSL context    
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Load tickers from the file
def load_tickers_from_file(file_path="ticker.txt"):
    try:
        with open(file_path, "r") as file:
            tickers = [line.strip() for line in file if line.strip()]
        return tickers
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []

# Fetch stock data for the loaded tickers
def fetch_stock_data(tickers):
    stock_data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Safely handle missing or invalid data
            change = info.get('regularMarketChange', None)
            if change is None:
                # Compute change as (current price - previous close)
                current_price = info.get('currentPrice', None)
                previous_close = info.get('regularMarketPreviousClose', None)
                if current_price is not None and previous_close is not None:
                    change = current_price - previous_close
                else:
                    change = 0  # Default to 0 if both fields are unavailable

            
            stock_data.append({
                'Symbol': ticker,
                'Current Price': info.get('currentPrice', 'N/A'),
                'Change': change,
            })
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    return stock_data


# Load tickers and fetch stock data
tickers = load_tickers_from_file("ticker.txt")
trending_tickers = fetch_stock_data(tickers)

# Load watchlist from file
def load_watchlist(file_path="watchlist.txt"):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []  # Return an empty list if the file doesn't exist

watchlist = load_watchlist()

# Function to fetch top gainers using the Financial Modeling Prep API
def get_top_gainers():
    api_key = "55GylMwJmoAOy6qXpyKd7BxgkIQrYgI6"
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={api_key}"
    try:
        response = urlopen(url, context=ssl_context)
        data = json.loads(response.read().decode("utf-8"))
        gainers = []
        for stock in data:
            gainers.append({
                "Ticker": stock.get("symbol", "N/A"),
                "Price": stock.get("price", 0),
                "Change": stock.get("changesPercentage", 0),
                "Company": stock.get("name", "Unknown")
            })
        return gainers
    except Exception as e:
        print(f"Error fetching top gainers: {e}")
        return []

# Function to fetch stock details
def get_stock_details(tickers):
    stock_data = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            current_price = data['Close'].iloc[-1]
            open_price = data['Open'].iloc[-1]
            volume = data['Volume'].iloc[-1]
            percent_change = ((current_price - open_price) / open_price) * 100
            stock_data.append({
                "Ticker": ticker,
                "Price": current_price,
                "Change": percent_change,
                "Volume": volume
            })
    return stock_data

# Function to fetch news for watchlist symbols using FMP
def fetch_watchlist_news():
    """Fetch news using Financial Modeling Prep API."""
    api_key = "55GylMwJmoAOy6qXpyKd7BxgkIQrYgI6"  # Replace with your valid API key
    url = f"https://financialmodelingprep.com/api/v3/fmp/articles?page=0&size=5&apikey={api_key}"
    all_news = []
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        response = urlopen(url, context=ssl_context)
        raw_data = response.read().decode("utf-8")
        data = json.loads(raw_data)
        # Extract the 'content' key which contains the list of articles
        articles = data.get("content", [])
        for article in articles:
            all_news.append({
                "title": article.get("title", "No Title"),
                "tickers": article.get("tickers", ""),
                "link": article.get("link", "#")
            })
    except Exception as e:
        print(f"Error fetching news: {e}")
    return all_news


# Layout
app.layout = dbc.Container([
    # Scrolling Ticker Section
    html.Div(
        id="scrolling-ticker",
        style={
            "overflow": "hidden",
            "whiteSpace": "nowrap",
            "width": "100%",
            "backgroundColor": "#f8f9fa",
            "padding": "10px",
            "borderBottom": "1px solid #ccc",
            "animation": "scrolling-text 20s linear infinite"
        },
        children=[
            html.Span(
                [
                    html.Span(ticker["Symbol"], style={"color": "blue", "marginRight": "10px"}),
                    html.Span(f"${ticker['Current Price']}", style={"color": "black", "marginRight": "10px"}),
                    html.Span(
                        f"{ticker['Change']:+.2f}",
                        style={
                            "color": "green" if ticker["Change"] > 0 else "red" if ticker["Change"] < 0 else "black",
                            "marginRight": "15px"
                        }
                    )
                ]
            ) for ticker in trending_tickers
        ]
    ),

    dcc.Interval(
        id="ticker-interval",
        interval=60 * 1000,  # Update every 60 seconds
        n_intervals=0
    ),


    # Main Title
    html.H1("Stock Market Dashboard", className="text-center mt-4 mb-4"),

    # News Section
    dbc.Row([
        dbc.Col([
            html.H2("News", className="center-title"),
            html.Div(
                id="scrolling-news",
                style={
                    "overflow": "hidden",
                    "whiteSpace": "nowrap",
                    "width": "100%",
                    "background": "#f8f9fa",
                    "padding": "10px",
                    "animation": "scrolling-text 90s linear infinite"
                }
            )
        ])
    ], className="mt-4"),

    # Watchlist, Top Gainers, and Stock Chart Section
    dbc.Row([
        # Watchlist
        dbc.Col([
            html.H2("Watchlist", className="center-title"),
            dbc.Table(id="watchlist-table", bordered=True, hover=True, striped=True, responsive=True)
        ], width=4, style={"border-right": "1px solid #ccc", "padding-right": "15px"}),

        # Top Gainers
        dbc.Col([
            html.H2("Top Gainers", className="center-title"),
            dbc.Table(id="top-gainers-table", bordered=True, hover=True, striped=True, responsive=True)
        ], width=4, style={"padding-left": "15px", "padding-right": "15px"}),

        # Stock Chart
        dbc.Col([
            html.H2("Stock Chart", className="center-title"),
            dcc.Graph(id="stock-chart", style={"height": "400px"})
        ], width=4)
    ], style={"display": "flex", "align-items": "start", "margin-top": "20px"})
], fluid=True)

# Callback for Scrolling Ticker
@app.callback(
    Output("scrolling-ticker", "style"),
    Input("scrolling-ticker", "id")  # Trigger once on load
)
def adjust_ticker_width(_):
    ticker_count = len(trending_tickers)
    total_width = max(6500, ticker_count * 200)  # Adjust the multiplier as needed
    duration = total_width / 50  # Adjust speed factor (50 pixels per second)
    return {
        "overflow": "hidden",
        "whiteSpace": "nowrap",
        "width": f"{total_width}px",
        "backgroundColor": "#f8f9fa",
        "padding": "10px",
        "borderBottom": "1px solid #ccc",
        "animation": "scrolling-text 180s linear infinite"  # Ensure animation is applied
    }

# Callback for Watchlist News
@app.callback(
    Output("scrolling-news", "children"),
    Input("scrolling-news", "id")  # Triggered once on load
)
def update_watchlist_news(_):
    news_items = fetch_watchlist_news()
    print(f"Number of news items: {len(news_items)}")
    for item in news_items:
        print(item)  # Log the content of each news item
        
    if not news_items:
        return "No news available."
    
    # Render each news item with proper spacing
    return [
        html.Span(
            dcc.Link(f"{item['title']} [{item['tickers']}]",
                     href=item['link'], target="_blank"),
            style={"margin-right": "50px"}  # Add spacing between items
        )
        for item in news_items
    ]

# Callback to Dynamically Adjust Scrolling News Width
@app.callback(
    Output("scrolling-news", "style"),
    Input("scrolling-news", "id")  # Triggered once on load
)
def adjust_scrolling_style(_):
    news_items = fetch_watchlist_news()
    item_count = len(news_items)
    total_width = max(4000, item_count * 300)  # Estimate total width (300px per item)
    return {
        "overflow": "hidden",
        "whiteSpace": "nowrap",
        "width": f"{total_width}px",  # Dynamically set width
        "background": "#f8f9fa",
        "padding": "10px",
        "animation": "scrolling-text 90s linear infinite"
    }


# Callback for Watchlist Table
@app.callback(
    Output("watchlist-table", "children"),
    Input("watchlist-table", "id")
)
def update_watchlist_table(_):
    stock_details = get_stock_details(watchlist)
    table_header = [
        html.Thead(html.Tr([html.Th("Ticker"), html.Th("Price"), html.Th("Change (%)"), html.Th("Volume")]))
    ]
    table_rows = [
        html.Tr([
            html.Td(html.Button(stock["Ticker"], id={"type": "stock-ticker", "index": stock["Ticker"]})),
            html.Td(f"${stock['Price']:.2f}"),
            html.Td(f"{stock['Change']:.2f}%", style={"color": "green" if stock["Change"] > 0 else "red"}),
            html.Td(f"{stock['Volume']:,}")
        ]) for stock in stock_details
    ]
    return table_header + [html.Tbody(table_rows)]

# Callback for Top Gainers Table
@app.callback(
    Output("top-gainers-table", "children"),
    Input("top-gainers-table", "id")
)
def update_top_gainers(_):
    gainers = get_top_gainers()
    if not gainers:
        return [html.Tbody([html.Tr([html.Td("No data available")])])]

    table_header = [
        html.Thead(html.Tr([html.Th("Ticker"), html.Th("Company"), html.Th("Price"), html.Th("Change")]))
    ]
    table_rows = [
        html.Tr([
            html.Td(html.Button(stock["Ticker"], id={"type": "stock-ticker", "index": stock["Ticker"]})),
            html.Td(stock["Company"]),
            html.Td(f"${stock['Price']:.2f}"),
            html.Td(f"{stock['Change']:.2f}%", style={"color": "green" if float(stock["Change"]) > 0 else "red"})
        ]) for stock in gainers
    ]
    return table_header + [html.Tbody(table_rows)]

# Callback for Stock Chart
@app.callback(
    Output("stock-chart", "figure"),
    Input({"type": "stock-ticker", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def update_stock_chart(ticker_clicks):
    ctx_trigger = ctx.triggered_id
    if not ctx_trigger or not ticker_clicks:
        return {}
    ticker = ctx_trigger["index"]

    # Fetch stock data
    stock = yf.Ticker(ticker)
    data = stock.history(period="1mo")
    if data.empty:
        return {}

    # Create the figure
    return {
        "data": [
            {
                "x": data.index,
                "y": data["Close"],
                "type": "line",
                "name": ticker
            }
        ],
        "layout": {
            "title": f"{ticker} Stock Price (Last 1 Month)",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Price (USD)"}
        }
    }

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))  # Use the PORT environment variable if available
    app.run_server(host="0.0.0.0", port=port, debug=False)

