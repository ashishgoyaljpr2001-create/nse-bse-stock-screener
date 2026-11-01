import io
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import yfinance as yf
import requests

st.set_page_config(page_title='NSE Loss + CFO Scanner V2', layout='wide')
st.title('NSE Market Scanner — Losses with Positive Operating Cash Flow')
st.caption('Free NSE listing + Yahoo Finance financial statements. Results are preliminary; verify annual reports and consolidated financials.')

NSE_CSV = 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv'

@st.cache_data(ttl=86400, show_spinner=False)
def load_nse_symbols():
    headers = {'User-Agent':'Mozilla/5.0 (compatible; financial research)', 'Accept':'text/csv,*/*', 'Referer':'https://www.nseindia.com/'}
    response = requests.get(NSE_CSV, headers=headers, timeout=25)
    response.raise_for_status()
    df = pd.read_csv(io.BytesIO(response.content))
    df.columns = df.columns.str.strip()
    if 'SYMBOL' not in df.columns:
        raise ValueError('Unexpected NSE listing file format')
    if ' SERIES' in df.columns:
        df = df[df[' SERIES'].astype(str).str.strip().eq('EQ')]
    elif 'SERIES' in df.columns:
        df = df[df['SERIES'].astype(str).str.strip().eq('EQ')]
    return sorted({str(x).strip().upper()+'.NS' for x in df['SYMBOL'].dropna() if str(x).strip()})

def to_cr(value):
    return float(value)/1e7

def get_row(frame, candidates):
    for key in candidates:
        if key in frame.index:
            row = frame.loc[key]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            return row
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_financials(symbol):
    ticker = yf.Ticker(symbol)
    inc = ticker.income_stmt
    cf = ticker.cashflow
    if inc is None or cf is None or inc.empty or cf.empty:
        return {'status':'Missing income statement or cash flow'}
    profit = get_row(inc, ['Net Income','Net Income Common Stockholders','Net Income From Continuing And Discontinued Operation'])
    ops = get_row(cf, ['Operating Cash Flow','Cash Flow From Continuing Operating Activities','Total Cash From Operating Activities'])
    if profit is None or ops is None:
        return {'status':'PAT or operating cash flow row unavailable'}
    a = {pd.Timestamp(k).strftime('%Y-%m-%d'):v for k,v in profit.items() if pd.notna(v)}
    b = {pd.Timestamp(k).strftime('%Y-%m-%d'):v for k,v in ops.items() if pd.notna(v)}
    dates = sorted(set(a).intersection(b), reverse=True)
    if not dates: return {'status':'No matching annual statement dates'}
    return {'status':'OK', 'years':[(d, to_cr(a[d]),to_cr(b[d])) for d in dates]}

def evaluate(symbol, periods, min_cfo):
    try:
        data = fetch_financials(symbol)
        if data['status'] != 'OK': return {'Ticker':symbol,'Status':data['status'],'Years available':0}
        years = data['years']
        row = {'Ticker':symbol, 'Years available':len(years)}
        for i, (date, pat, cfo) in enumerate(years[:4], 1):
            row[f'FY{i} ending'] = date
            row[f'FY{i} PAT ₹cr'] = round(pat,2)
            row[f'FY{i} CFO ₹cr'] = round(cfo,2)
        if len(years)<periods:
            row['Status']=f'Insufficient years ({len(years)}/{periods})'
        else:
            selected=years[:periods]
            row['Cumulative CFO ₹cr']=round(sum(x[2] for x in selected),2)
            failed_pat=[x[0] for x in selected if x[1]>=0]
            failed_cfo=[x[0] for x in selected if x[2]<=min_cfo]
            if not failed_pat and not failed_cfo: row['Status']='MATCH'
            else:
                reasons=[]
                if failed_pat: reasons.append('PAT not negative: '+', '.join(failed_pat))
                if failed_cfo: reasons.append('CFO below/equal threshold: '+', '.join(failed_cfo))
                row['Status']='; '.join(reasons)
        return row
    except Exception as exc:
        return {'Ticker':symbol,'Status':f'Fetch error: {str(exc)[:140]}'}

with st.sidebar:
    periods=st.selectbox('Consecutive annual periods', [2,3,4], index=2)
    min_cfo=st.number_input('Minimum operating CFO each year (₹ crore)', value=0.0, step=1.0)
    batch_size=st.select_slider('Companies per batch', options=[10,20,25,50], value=20)
    pause=st.slider('Pause between companies (seconds)',0.0,3.0,0.7,0.1)
    st.info('Free Yahoo Finance data can be incomplete, rate-limited or standalone. Four annual periods is often the maximum available.')

st.subheader('1. Load company universe')
upload=st.file_uploader('Optional: upload CSV with a Symbol column (e.g. RELIANCE.NS)', type='csv')
if 'symbols' not in st.session_state: st.session_state.symbols=[]
if 'rows' not in st.session_state: st.session_state.rows=[]
if 'position' not in st.session_state: st.session_state.position=0
if 'settings' not in st.session_state: st.session_state.settings=None

c1,c2=st.columns(2)
with c1:
    if st.button('Load all NSE equity symbols', type='primary'):
        try:
            syms=load_nse_symbols()
            st.session_state.symbols=syms
            st.session_state.rows=[]
            st.session_state.position=0
            st.session_state.settings=None
            st.success(f'Loaded {len(syms)} NSE symbols.')
        except Exception as exc:
            st.error(f'NSE listing could not be downloaded: {exc}. Upload a symbol CSV instead.')
with c2:
    if upload is not None and st.button('Use uploaded CSV'):
        try:
            frame=pd.read_csv(upload)
            col=next((c for c in frame.columns if c.strip().lower() in ['symbol','ticker']), None)
            if col is None: st.error('CSV must contain a Symbol or Ticker column.')
            else:
                syms=[]
                for s in frame[col].dropna().astype(str):
                    s=s.strip().upper()
                    if not s.endswith(('.NS','.BO')): s+='.NS'
                    if s: syms.append(s)
                st.session_state.symbols=list(dict.fromkeys(syms))
                st.session_state.rows=[]
                st.session_state.position=0
                st.session_state.settings=None
                st.success(f'Loaded {len(st.session_state.symbols)} symbols.')
        except Exception as exc: st.error(str(exc))

st.write(f"**Universe:** {len(st.session_state.symbols):,} tickers | **Checked:** {st.session_state.position:,}")
st.subheader('2. Scan in batches')
current_settings=(periods,min_cfo)
if st.session_state.settings is not None and st.session_state.settings != current_settings:
    st.warning('Criteria changed. Reset results before scanning again to avoid mixing screening criteria.')
reset=st.button('Reset screening results')
if reset:
    st.session_state.rows=[]
    st.session_state.position=0
    st.session_state.settings=None
    st.rerun()

can_scan=bool(st.session_state.symbols) and st.session_state.position<len(st.session_state.symbols) and (st.session_state.settings is None or st.session_state.settings==current_settings)
if st.button('Scan next batch', disabled=not can_scan, type='primary'):
    st.session_state.settings=current_settings
    start=st.session_state.position
    end=min(start+batch_size,len(st.session_state.symbols))
    progress=st.progress(0)
    label=st.empty()
    for i in range(start,end):
        symbol=st.session_state.symbols[i]
        label.write(f'Checking {i+1:,} / {len(st.session_state.symbols):,}: {symbol}')
        st.session_state.rows.append(evaluate(symbol,periods,min_cfo))
        st.session_state.position=i+1
        progress.progress((i-start+1)/(end-start))
        if i<end-1: time.sleep(pause)
    st.rerun()

if st.session_state.symbols:
    st.progress(st.session_state.position/len(st.session_state.symbols))
if st.session_state.rows:
    result=pd.DataFrame(st.session_state.rows)
    matches=result[result['Status'].eq('MATCH')].copy()
    st.metric('Qualifying companies',len(matches))
    st.metric('Companies checked',len(result))
    st.subheader('Matching companies')
    st.dataframe(matches, use_container_width=True, hide_index=True)
    st.download_button('Download matches CSV', matches.to_csv(index=False).encode('utf-8-sig'), 'nse_matching_stocks.csv', 'text/csv')
    with st.expander('All companies — including non-matches, missing data and errors'):
        st.dataframe(result, use_container_width=True, hide_index=True)
    st.download_button('Download full audit CSV', result.to_csv(index=False).encode('utf-8-sig'), 'nse_full_screening_audit.csv', 'text/csv')

st.caption('Method: each of the latest N available matching annual statement dates must have PAT < 0 and operating CFO > threshold. No claim of comprehensive exchange coverage, and no investment recommendation.')
