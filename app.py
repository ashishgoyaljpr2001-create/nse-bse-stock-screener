import streamlit as st
import pandas as pd
import yfinance as yf
from io import BytesIO
import time

st.set_page_config(page_title='Free NSE/BSE Cash Flow Screener',layout='wide')
st.title('Loss-making, cash-generating NSE/BSE companies')
st.caption('Free Yahoo Finance data via yfinance. Coverage, fiscal-year alignment and consolidated reporting are not guaranteed. Verify exchange filings before investing.')
with st.sidebar:
    years=st.selectbox('Consecutive annual periods',[2,3,4],index=2)
    min_cfo=st.number_input('Minimum CFO each year (₹ crore)',min_value=0.,value=0.)
    pause=st.slider('Pause between companies (seconds)',0.2,3.0,0.7)
    st.info('Free Yahoo Finance data often covers only four annual periods; larger universes may be slow or rate-limited.')
default='IDEA.NS, YESBANK.NS, SUZLON.NS, ZOMATO.NS'
symbols=st.text_area('Enter Yahoo Finance tickers (.NS or .BO), comma or newline separated',default,height=100)
file=st.file_uploader('Optional: CSV containing a Symbol column (e.g. IDEA.NS)',type='csv')

def find_row(df, candidates):
    for name in candidates:
        if name in df.index: return df.loc[name]
    return None

def get_annual(ticker):
    t=yf.Ticker(ticker)
    inc=t.income_stmt
    cash=t.cashflow
    if inc is None or cash is None or inc.empty or cash.empty: return None,'Missing income statement or cash flow'
    pat=find_row(inc,['Net Income','Net Income Common Stockholders','Net Income Continuous Operations'])
    cfo=find_row(cash,['Operating Cash Flow','Cash Flow From Continuing Operating Activities'])
    if pat is None or cfo is None: return None,'Missing PAT or CFO line'
    a=pd.DataFrame({'PAT':pat,'CFO':cfo})
    a.index=pd.to_datetime(a.index)
    a=a.dropna().sort_index(ascending=False)
    a=a[~a.index.year.duplicated(keep='first')]
    if len(a)<years: return None,f'Only {len(a)} complete annual periods'
    a=a.iloc[:years].copy()
    if not all((a['PAT']<0)&(a['CFO']>min_cfo*1e7)): return None,'Does not match criteria'
    return a,None

if st.button('Run free online screening',type='primary'):
    raw=[x.strip().upper() for x in symbols.replace('\n',',').split(',') if x.strip()]
    if file:
        uploaded=pd.read_csv(file)
        if 'Symbol' not in uploaded: st.error('CSV requires Symbol column');st.stop()
        raw+=uploaded.Symbol.dropna().astype(str).str.strip().str.upper().tolist()
    raw=list(dict.fromkeys(raw))
    if not raw: st.error('Enter at least one ticker');st.stop()
    results=[];logs=[];progress=st.progress(0)
    for i,sym in enumerate(raw):
        if not sym.endswith(('.NS','.BO')): sym+='.NS'
        try:
            data,error=get_annual(sym)
            if error: logs.append({'Ticker':sym,'Status':error})
            else:
                r={'Ticker':sym,'Periods':years,'Total PAT (₹ cr)':round(data.PAT.sum()/1e7,2),'Total CFO (₹ cr)':round(data.CFO.sum()/1e7,2)}
                for dt,v in data.iterrows():
                    label=dt.strftime('%Y-%m-%d')
                    r[f'PAT {label} (₹ cr)']=round(v.PAT/1e7,2)
                    r[f'CFO {label} (₹ cr)']=round(v.CFO/1e7,2)
                results.append(r)
        except Exception as e: logs.append({'Ticker':sym,'Status':f'Error: {str(e)[:150]}'})
        progress.progress((i+1)/len(raw));time.sleep(pause)
    st.subheader(f'Matches: {len(results)} of {len(raw)} tickers checked')
    if results:
        output=pd.DataFrame(results).sort_values('Total CFO (₹ cr)',ascending=False)
        st.dataframe(output,use_container_width=True)
        out=BytesIO()
        with pd.ExcelWriter(out,engine='openpyxl') as w:
            output.to_excel(w,index=False,sheet_name='Matches')
            pd.DataFrame(logs).to_excel(w,index=False,sheet_name='Not matched')
        st.download_button('Download Excel',out.getvalue(),'free_cashflow_screener.xlsx')
    if logs:
        with st.expander('Non-matches, errors and missing data'):
            st.dataframe(pd.DataFrame(logs),use_container_width=True)
    st.warning('Results are preliminary: Yahoo Finance may provide standalone rather than consolidated statements and may have different fiscal year-end dates. This scans only the supplied ticker universe, not automatically every NSE/BSE listing.')
