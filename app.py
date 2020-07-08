
# todo: hover text, spacing, styling, text, heroku, refactor, comment
# todo later: loading bar, update/refresh, constant sector color, click bubble for more company info
import datetime
import pickle
import pandas as pd
import pandas_datareader.data as web
from yahoo_fin import stock_info as si
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import yfinance as yf

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

app = dash.Dash('StockViz')

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

app.layout = html.Div(
    # style={'backgroundColor': colors['background']},
    children=[
        html.H1('StockViz'),
        html.Hr(),

        dcc.Dropdown(
            id = 'dropdown',
            options=[
                {'label': "Today's Biggest Gainers", 'value': 'gainers'},
                {'label': "Today's Biggest Losers", 'value': 'losers'},
            ],
            value='gainers',
            style=dict(
                width='40%'
            )
            
        ),
        html.Div(id='main-graph'),
        dcc.Markdown('''
        ### Today's biggest gainers and losers
        - y axis shows day's % price change
        - x axis shows day's volume as % of 3 month avg. volume
        - bubble size represents stock's market cap
        - bubble color represents stock's GICS sector
        - choose gainers or losers from dropdown menu
        - data sources
            - gainers data source: https://finance.yahoo.com/gainers
            - losers: https://finance.yahoo.com/losers
            - stocks with avg. volume < 1,000,000 are filtered out
        '''),
        html.Hr(),
        html.Div(children='Symbol to graph:'),
        dcc.Input(id='input', value='aapl', type='text'),
        html.Div(id='output-graph'),
        
    ]
)


@app.callback(
    Output(component_id='main-graph', component_property='children'),
    [Input(component_id='dropdown', component_property='value')]
)
def bubble_chart(value):
    funcs = {'gainers': si.get_day_gainers, 'losers': si.get_day_losers}
    df = funcs[value]()
    
    df['Volume'] = df['Volume'].apply(lambda x: x / 10 ** 9 if x > 10 ** 10 else x)
    df['Avg Vol (3 month)'] = df['Avg Vol (3 month)'].apply(lambda x: x / 10 ** 9 if x > 10 ** 10 else x)
    df = df[df['Avg Vol (3 month)'] > 1000000]
    
    with open('sectors.pickle', 'rb') as f:
        sectors = pickle.load(f)
    
    def get_sector(ticker):
        return yf.Ticker(ticker).get_info().get('sector')
    
    for i, ticker in enumerate(df['Symbol']):
        if ticker not in sectors.keys():
            try:
                sectors[ticker] = get_sector(ticker)
            except:
                sectors[ticker] = 'unknown'
    
    with open('sectors.pickle', 'wb') as f:
        pickle.dump(sectors, f)
    
    cols = ['Symbol', '% Change', 'Market Cap']
    adf = df[cols].copy()
    adf['% Avg Vol'] = 100 * df['Volume'] / df['Avg Vol (3 month)']
    adf['Sector'] = adf['Symbol'].apply(sectors.get)
    
    def clean_mc(mcs):
        if not isinstance(mcs, str):
            return mcs
        else:
            for char in mcs:
                if char.isalpha():
                    i = mcs.index(char)
                    break
            market_cap_str = mcs[:i + 1]
            letter = market_cap_str[-1]
            number = float(market_cap_str[:-1])
            letter_dict = {
                'M': 1000000,
                'B': 1000000000,
                'T': 1000000000000
            }
            market_cap = number * letter_dict[letter]
            return market_cap
    
    adf['Market Cap'] = adf['Market Cap'].apply(clean_mc)
    adf['Market Cap (B)'] = adf['Market Cap'] / 1000000000
    
    fig = px.scatter(adf, x="% Avg Vol", y="% Change", hover_data=['Symbol'], size='Market Cap (B)', color='Sector',
                     size_max=40,
                     # height=800, width=1200,
                     # template='plotly_dark'
                     )
    return dcc.Graph(id='main', figure=fig)


@app.callback(
    Output(component_id='output-graph', component_property='children'),
    [Input(component_id='input', component_property='value')]
)
def update_value(input_data):
    start = datetime.datetime(2015, 1, 1)
    end = datetime.datetime.now()
    df = si.get_data(input_data, start_date=start, end_date=end)

    return dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': df.index, 'y': df.close, 'type': 'line', 'name': input_data},
            ],
            'layout': {
                'title': input_data,
                # 'template': pio.templates['plotly_dark']
            }
        }
    )

if __name__ == '__main__':
    app.run_server(debug=True, port=8891)