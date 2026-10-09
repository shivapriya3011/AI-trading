import os, json, sqlite3, base64, hashlib, io
from datetime import datetime
import streamlit as st
from PIL import Image

st.set_page_config(page_title='AI Trading Mentor', page_icon='📈', layout='wide')
DB='trades.db'
ENTRY_MODELS=['Counter Buy','Counter Sell','Impulse Breakout Buy','Impulse Breakout Sell','Complete Breakout Buy','Complete Breakout Sell','S/R Buy','S/R Sell','Wickfill','Impulse / A+','Pullback Buy','Pullback Sell','Fakeout Buy','Fakeout Sell','Big Body Breakout','Not sure']
SESSIONS=['Asian','Mid Asian → London Open','Pre-New York → New York','Other / Not sure']
TRENDS=['Bullish','Bearish','Range / Neutral','Not sure']
CONFIRMATIONS=['Break of Previous High / Low','Re-break','Flip','Own High / Low Break','Wick Entry','Pullback Confirmation','No Clear Confirmation','Not sure']

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, direction TEXT, entry REAL, sl REAL, tp REAL, timeframe TEXT, session TEXT, entry_model TEXT, m30 TEXT, h1 TEXT, current_trend TEXT, htf_zone TEXT, confirmation TEXT, reason TEXT, screenshot BLOB, analysis TEXT, outcome TEXT DEFAULT 'Open')'''); c.commit(); return c

def analyse_with_ai(details, img_bytes):
    # AI analysis is optional; app still provides a transparent rule-based review without an API key.
    key=os.getenv('OPENAI_API_KEY','')
    try:
        if not key:
            return rule_review(details)
        from openai import OpenAI
        client=OpenAI(api_key=key)
        content=[{'type':'input_text','text': 'You are a cautious trading mentor. Analyse the supplied trade screenshot and user-entered context. Do not claim certainty or invent unreadable chart prices. State what can/cannot be verified, setup strengths/weaknesses, invalidation, and risk-reward. Educational only, not financial advice.\nTRADE DETAILS:\n'+json.dumps(details,ensure_ascii=False)}]
        if img_bytes:
            im=Image.open(io.BytesIO(img_bytes)).convert('RGB'); im.thumbnail((1400,1400)); b=io.BytesIO(); im.save(b,format='JPEG',quality=82)
            content.append({'type':'input_image','image_url':'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()})
        res=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),input=[{'role':'user','content':content}],max_output_tokens=900)
        return res.output_text
    except Exception as e:
        return rule_review(details)+'\n\nAI service error: '+str(e)+'\nCheck your API key/model or try again.'

def rule_review(d):
    entry,sl,tp=float(d['entry']),float(d['sl']),float(d['tp'])
    risk=abs(entry-sl); reward=abs(tp-entry); rr=reward/risk if risk else 0
    valid=(sl<entry<tp) if d['direction']=='Buy' else (sl>entry>tp)
    return (f"**Initial checks**\n\n- Direction: {d['direction']}\n- Entry / SL / TP: {entry:g} / {sl:g} / {tp:g}\n- Risk distance: {risk:g}; reward distance: {reward:g}; risk-to-reward: 1:{rr:.2f}\n- Price ordering: {'Valid' if valid else 'Invalid — check SL/TP relative to entry'}\n- Entry model: {d['entry_model']}\n- Context: M30 {d['m30']}; H1 {d['h1']}; session {d['current_trend']}\n\n**Mentor note:** This basic review cannot verify chart structure or entry confirmation without AI chart analysis. Confirm the setup against your actual chart, keep risk controlled, and do not treat this as a guaranteed signal.")

conn().close()
st.markdown('''<style>.stApp{background:#fff8d6}.block-container{max-width:1050px;padding-top:1.5rem}.stButton>button{border-radius:10px;font-weight:600}.metric-card{background:white;padding:16px;border-radius:12px;border:1px solid #e5dcae}</style>''',unsafe_allow_html=True)
st.title('📈 AI Trading Mentor')
st.caption('Analyse your trade based on your own trading strategy')
page=st.sidebar.radio('Navigation',['Trade Analysis','Trade Journal','Dashboard'])

if page=='Trade Analysis':
    st.subheader('Trade Details')
    screenshot=st.file_uploader('Upload Trade Screenshot',type=['png','jpg','jpeg'],help='PNG or JPG chart screenshot')
    c1,c2=st.columns(2)
    with c1:
        direction=st.selectbox('Trade Direction',['Buy','Sell'])
        entry=st.number_input('Entry Price',min_value=0.0,format='%.3f')
        sl=st.number_input('Stop Loss',min_value=0.0,format='%.3f')
        tp=st.number_input('Take Profit',min_value=0.0,format='%.3f')
        timeframe=st.selectbox('Execution Timeframe',['15M','M30','H1','H4','Daily'])
    with c2:
        session=st.selectbox('Trading Session',SESSIONS)
        model=st.selectbox('Entry Model',ENTRY_MODELS)
        m30=st.selectbox('M30 Trend / Context',TRENDS)
        h1=st.selectbox('H1 Trend / Context',TRENDS)
        current=st.selectbox('Current Session Trend',TRENDS)
        zone=st.selectbox('H1 / H4 Zone Nearby?',['Yes','No','Not sure'])
        confirmation=st.selectbox('Entry Confirmation',CONFIRMATIONS)
    reason=st.text_area('Why did you take this trade?',placeholder='Explain your reason for entering this trade...')
    if screenshot: st.image(screenshot,caption='Uploaded chart',use_container_width=True)
    if st.button('🔍 Analyse Trade',type='primary',use_container_width=True):
        if not screenshot: st.error('Please upload a trade screenshot.')
        elif not entry or not sl or not tp: st.error('Enter Entry, Stop Loss and Take Profit.')
        elif direction=='Buy' and not sl<entry<tp: st.error('For a Buy trade, Stop Loss < Entry < Take Profit.')
        elif direction=='Sell' and not sl>entry>tp: st.error('For a Sell trade, Stop Loss > Entry > Take Profit.')
        else:
            details={'direction':direction,'entry':entry,'sl':sl,'tp':tp,'timeframe':timeframe,'session':session,'entry_model':model,'m30':m30,'h1':h1,'current_trend':current,'htf_zone':zone,'confirmation':confirmation,'reason':reason}
            # No persistent 'analysing' lock: each request completes or returns an error, preventing the stuck state.
            with st.spinner('Analysing your trade…'):
                result=analyse_with_ai(details,screenshot.getvalue())
            st.session_state['latest_analysis']=result; st.session_state['latest_details']=details; st.session_state['latest_image']=screenshot.getvalue()
            st.success('Analysis complete')
    if st.session_state.get('latest_analysis'):
        st.subheader('Analysis Result'); st.markdown(st.session_state['latest_analysis'])
        if st.button('💾 Save to Trade Journal',use_container_width=True):
            d=st.session_state['latest_details']; c=conn()
            c.execute('INSERT INTO trades(created,direction,entry,sl,tp,timeframe,session,entry_model,m30,h1,current_trend,htf_zone,confirmation,reason,screenshot,analysis) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),d['direction'],d['entry'],d['sl'],d['tp'],d['timeframe'],d['session'],d['entry_model'],d['m30'],d['h1'],d['current_trend'],d['htf_zone'],d['confirmation'],d['reason'],st.session_state.get('latest_image'),st.session_state['latest_analysis']))
            c.commit(); c.close(); st.success('Trade saved to journal.')
elif page=='Trade Journal':
    st.title('📖 Trade Journal'); c=conn(); rows=c.execute('SELECT * FROM trades ORDER BY id DESC').fetchall()
    if not rows: st.info('No trades saved yet. Analyse a trade and select Save to Trade Journal.')
    for r in rows:
        with st.expander(f"{r['created']} · {r['direction']} · {r['entry_model']} · {r['timeframe']}"):
            a,b,d=st.columns(3); a.metric('Entry',r['entry']); b.metric('Stop Loss',r['sl']); d.metric('Take Profit',r['tp'])
            st.write('Session:',r['session'],'| M30:',r['m30'],'| H1:',r['h1']); st.write('Reason:',r['reason']); st.markdown(r['analysis'] or '')
            if r['screenshot']: st.image(bytes(r['screenshot']),use_container_width=True)
            if st.button('Delete trade',key=f"del{r['id']}"):
                c.execute('DELETE FROM trades WHERE id=?',(r['id'],)); c.commit(); st.rerun()
    c.close()
else:
    st.title('📊 Dashboard'); c=conn(); rows=c.execute('SELECT * FROM trades ORDER BY id DESC').fetchall(); c.close()
    total=len(rows); buy=sum(1 for r in rows if r['direction']=='Buy'); sell=total-buy
    a,b,d=st.columns(3); a.metric('Total Trades',total); b.metric('Buy Trades',buy); d.metric('Sell Trades',sell)
    if rows:
        st.subheader('Recent Trades'); st.dataframe([{'Date':r['created'],'Direction':r['direction'],'Model':r['entry_model'],'Entry':r['entry'],'SL':r['sl'],'TP':r['tp'],'Timeframe':r['timeframe']} for r in rows],use_container_width=True,hide_index=True)
    else: st.info('Your saved trade statistics will appear here.')
st.sidebar.divider(); st.sidebar.caption('AI analysis needs an OpenAI API key. Without it, basic risk/reward checks still work.')
