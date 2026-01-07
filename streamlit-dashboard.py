import streamlit as st
import pandas as pd
import datetime
from datetime import datetime as dt, timedelta
import time
import plotly.graph_objects as go
import plotly.express as px

# Try to import streamlit-mermaid if available, otherwise use simple visualization
try:
    from streamlit_mermaid import st_mermaid
    HAS_MERMAID = True
except ImportError:
    HAS_MERMAID = False

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="ENBD & EIB Dashboard",
    layout="wide"
)

# =========================
# USER DATABASE
# =========================
users = {
    "ctbonifacio": "admin",
    "dabaguas": "viewer",
    "jtortega": "viewer",
    "decajes": "viewer"
}

# Mapping agent user codes to full names (for merging uploaded REMARK BY values)
AGENT_USER_TO_NAME = {
    # ENBD
    "NCESCOPALAO": "Niecel Escopalao",
    "HPBONABON": "Henry Paolo P. Bonabon",
    "JTORTEGA": "John Vincent Ortega",
    "CGMEDALLA": "Cheska Mare Medalla",
    "CLCAMADO": "Christian Jeric Lajera Camado",
    "JCAYNO": "James Eduard Q. Cayno",
    "GCUENCA": "Gearbey M. Cuenca",
    "JPACULABA": "John Mark D. Paculaba",
    # EIB
    "DECAJES": "Dorithy Gail Cajes",
    "SBCANALES": "Samantha Nicole B. Canales"
}

# Status categories for account classification (from Reference sheet)
STATUS_RPC = [
    'POSITIVE CONTACT - EMAIL RESPONSIVE',
    'POSITIVE CONTACT - RETURNED IN PH_JOBLESS',
    'POSITIVE CONTACT - CLAIMING FULLY PAID',
    'POSITIVE CONTACT - TFIP',
    'POSITIVE CONTACT - UNDER MEDICATION',
    'POSITIVE CONTACT - NO INTENTION OF PAYING',
    'POSITIVE CONTACT - DISPUTE',
    'POSITIVE CONTACT - REQUEST SPP OTP',
    'POSITIVE CONTACT - REQUEST SPP IN INSALLMENT',
    'POSITIVE CONTACT - REQUEST PARTIAL PAYMENT',
    'POSITIVE CONTACT - REGISTERED NUMBER',
    'POSITIVE CONTACT - UNREGISTERED NUMBER',
    'POSITIVE CONTACT - REGISTERED EMAIL',
    'POSITIVE CONTACT - UNREGISTERED EMAIL',
    'BP - SETTLEMENT_INSTALLMENT',
    'BP - PARTIAL PAYMENT',
    'BP - ONE TIME PAYMENT',
    'BP - DOWN_PAYMENT',
    'BP - FOLLOW UP',
    'PTP - FOLLOW UP',
    'POSITIVE CONTACT - NEW RPC'
]

STATUS_POSITIVE = [
    'POSITIVE - SKIP_OVER STAY',
    'POSITIVE - RESPONSIVE VIA DEMAND LETTER',
    'POSITIVE - EMPLOYER POSITIVE',
    'POSITIVE - OTHER SMEDIA POSITIVE',
    'POSITIVE - ICP ACTIVE',
    'POSITIVE - MOHRE ACTIVE',
    'POSITIVE - FAILED PID VERIFICATION',
    'POSITIVE - EMPLOYMENT NO LONGER CONNECTED',
    'POSITIVE - REGISTERED NUMBER',
    'POSITIVE - UNREGISTERED NUMBER',
    'POSITIVE - REGISTERED EMAIL',
    'POSITIVE - UNREGISTERED EMAIL',
    'POSITIVE - NEW ACTIVE VISA',
    'PTP - NEW PARTIAL PAYMENT',
    'PTP - NEW ONE TIME PAYMENT',
    'PTP - NEW DOWN PAYMENT',
    'PTP - NEW SETTLEMENT INSTALLMENT'
]

STATUS_NEGATIVE = [
    'NEGATIVE - SENT EMPLOYEE VERIFICATION',
    'NEGATIVE - NO SMEDIA ACCOUNTS',
    'NEGATIVE - NO EMPLOYER RECORD',
    'NEGATIVE - WRONG NUMBER',
    'NEGATIVE - SENT DEMAND LETTER',
    'NEGATIVE - PROMO LETTER SENT',
    'NEGATIVE - CANCELLED VISA',
    'NEGATIVE - UNREGISTERED NUMBER',
    'NEGATIVE - REGISTERED NUMBER',
    'NEGATIVE - DEMAND LETTER',
    'NEGATIVE - UNREGISTERED EMAIL',
    'NEGATIVE - REGISTERED EMAIL',
    'NEGATIVE - EMPLOYMENT NO LONGER CONNECTED',
    'JUNK - FULLY EXHAUSTED',
    'DO NOT CALL - PENDING COMPLAINT',
    'DO NOT CALL - DECEASED',
    'RETURNS - PULLOUT',
    'RETURNS - FULLYPAID'
]

# =========================
# SESSION STATE INITIALIZATION
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.attempts = 0
    st.session_state.lock_time = None
    st.session_state.login_time = None

if "enbd_data" not in st.session_state:
    st.session_state.enbd_data = pd.DataFrame()

if "eib_data" not in st.session_state:
    st.session_state.eib_data = pd.DataFrame()

if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.date.today()

if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "ENBD"

if "pending_upload" not in st.session_state:
    st.session_state.pending_upload = None

# ┌─────────────────────────────────────────────────────────────────────────────────┐
# │         PASSWORD GENERATION & VALIDATION FUNCTIONS                              │
# └─────────────────────────────────────────────────────────────────────────────────┘

def generate_password():
    """Generate real-time password: mmddyyyy0 + attempts"""
    base_password = dt.now().strftime("%m%d%Y0")
    return str(int(base_password) + st.session_state.attempts)


# ────────────────────────────────────────────────────────────────────────────────────

def check_logout():
    """Check if session has exceeded 1 hour"""
    if st.session_state.login_time and dt.now() - st.session_state.login_time > timedelta(hours=1):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.login_time = None
        st.warning("⏱️ Session expired. Please log in again.")
        st.rerun()


# ────────────────────────────────────────────────────────────────────────────────────

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.login_time = None
    st.session_state.attempts = 0
    st.session_state.lock_time = None
    st.success("✓ Logged out successfully.")
    time.sleep(1)
    st.rerun()


# ────────────────────────────────────────────────────────────────────────────────────

def login_page():
    """Render login page"""
    st.markdown("""
    <div style='text-align: center; margin-bottom: 40px;'>
        <h1>🔐 ENBD & EIB Dashboard</h1>
        <p style='color: #666; font-size: 16px;'>Agent Performance Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        # Lockout check
        if st.session_state.lock_time and dt.now() < st.session_state.lock_time:
            remaining = (st.session_state.lock_time - dt.now()).seconds
            st.error(f"❌ Too many failed attempts. Account locked.")
            st.warning(f"⏱️ Try again in {remaining} seconds")
            time.sleep(1)
            st.rerun()
            return
        
        st.subheader("👤 Login")
        
        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Username",
                help="Enter your username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Real-time password",
                help="Password changes every day (mmddyyyy0 + attempts)"
            )
            
            # Display current password requirement
            current_pwd = generate_password()
           
            
            login_btn = st.form_submit_button("🔓 Login", use_container_width=True)
            
            if login_btn:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                elif username not in users:
                    st.error("❌ Username not found")
                    st.session_state.attempts += 1
                    if st.session_state.attempts >= 5:
                        st.session_state.lock_time = dt.now() + timedelta(minutes=1)
                else:
                    correct_password = generate_password()
                    if password == correct_password:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.attempts = 0
                        st.session_state.login_time = dt.now()
                        st.session_state.lock_time = None
                        st.success("✓ Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.attempts += 1
                        remaining_attempts = 5 - st.session_state.attempts
                        
                        if st.session_state.attempts >= 5:
                            st.session_state.lock_time = dt.now() + timedelta(minutes=1)
                            st.error("❌ Maximum attempts (5) exceeded. Locked for 1 minute.")
                        else:
                            st.error(f"❌ Incorrect password. Attempts remaining: {remaining_attempts}/5")
                            st.info(f"📍 Correct password: **{correct_password}**")


# ┌─────────────────────────────────────────────────────────────────────────────────┐
# │            DATA PROCESSING & TRANSFORMATION FUNCTIONS        │
# └─────────────────────────────────────────────────────────────────────────────────┘

def process_masterlist(df, start_date, client_name):
    """
    Process uploaded masterlist:
    - Extract AGENT_USER from REMARK BY column (required)
    - Only keep rows where REMARK BY maps to known agents
    - Auto-create missing columns
    """
    df_processed = df.copy()

    # REMARK BY column is required for agent mapping
    remark_by_col = None
    for col in df_processed.columns:
        if col.strip().upper() in ("REMARK BY", "REMARKBY"):
            remark_by_col = col
            break

    if remark_by_col is None:
        # No REMARK BY column found, 
        # return empty dataframe
        return pd.DataFrame(columns=[
            "AGENT_NAME", "TOTAL_WOA", "NEGATIVE", "RPC", "POSITIVE",
            "TOTAL_PTP_COUNT", "TOTAL_PAYMENT_COUNT", "TOTAL_TALK_TIME",
            "PTP_PERCENTAGE", "NEW_RPC", "NEW_ICP_ACTIVE", "GRADSE_PERCENTAGE",
            "START_DATE", "AGENT_USER"
        ])

    # Extract AGENT_USER from REMARK BY
    df_processed["AGENT_USER"] = df_processed[remark_by_col].astype(str).str.strip().str.upper()
    
    # Map AGENT_USER to AGENT_NAME using known mapping
    df_processed["AGENT_NAME"] = df_processed["AGENT_USER"].map(AGENT_USER_TO_NAME)
    
    # Filter: only keep rows with known agents (non-null AGENT_NAME)
    df_processed = df_processed[df_processed["AGENT_NAME"].notna()].copy()
    
    # Required columns
    required_columns = [
        "AGENT_NAME", "TOTAL_WOA", "NEGATIVE", "RPC", "POSITIVE",
        "TOTAL_PTP_COUNT", "TOTAL_PAYMENT_COUNT", "TOTAL_TALK_TIME",
        "PTP_PERCENTAGE", "NEW_RPC", "NEW_IDP_ACTIVE", "GRACE_PERCENTAGE"
    ]
    
    # Auto-create missing columns
    for col in required_columns:
        if col not in df_processed.columns:
            if "PERCENTAGE" in col:
                df_processed[col] = "0%"
            else:
                df_processed[col] = 0
    
    # Add START_DATE
    df_processed["START_DATE"] = start_date

    # Aggregate uploaded rows by AGENT_USER (sum numeric fields)
    agg_numeric = [c for c in required_columns if c not in ("AGENT_NAME",) and c not in ("PTP_PERCENTAGE", "GRACE_PERCENTAGE")]
    percent_cols = [c for c in required_columns if c in ("PTP_PERCENTAGE", "GRACE_PERCENTAGE")]

    grouped = df_processed.groupby("AGENT_USER").agg({
        "AGENT_NAME": "first",
        **{c: "sum" for c in agg_numeric if c in df_processed.columns},
        **{p: "first" for p in percent_cols if p in df_processed.columns},
        "START_DATE": "first"
    }).reset_index()

    # Reorder to required columns (ensure columns exist)
    for col in required_columns:
        if col not in grouped.columns:
            if "PERCENTAGE" in col:
                grouped[col] = "0%"
            else:
                grouped[col] = 0

    grouped["START_DATE"] = start_date

    return grouped[required_columns + ["START_DATE", "AGENT_USER"]]


# ────────────────────────────────────────────────────────────────────────────────────

def generate_woa(df, time_col=None, acct_col=None, agent_col=None, client_col=None):
    """
    Generate WOA lists and totals from a MASTERLIST-like DataFrame.
    Ranges:
      - first: 12:00 PM - 5:00 PM (inclusive)
      - second: 5:01 PM - 11:59:59 PM

    Returns: (first_df, second_df, total_first, total_second)
    """
    import pandas as _pd
    from datetime import time as _time

    if df is None or df.empty:
        return _pd.DataFrame(), _pd.DataFrame(), 0, 0

    dfw = df.copy()

    # Auto-detect columns if not provided
    cols_upper = {c: c.upper() for c in dfw.columns}
    if time_col is None:
        time_col = next((c for c, cu in cols_upper.items() if 'TIME' in cu or 'TIMESTAMP' in cu), None)
    if acct_col is None:
        acct_col = next((c for c, cu in cols_upper.items() if 'ACCT' in cu or 'ACCOUNT' in cu), None)
    if agent_col is None:
        agent_col = next((c for c, cu in cols_upper.items() if 'AGENT' in cu or 'REMARK' in cu), None)
    if client_col is None:
        client_col = next((c for c, cu in cols_upper.items() if 'CLIENT' in cu or cu in ('EIB','ENBD')), None)

    # If we don't have required columns, return empties
    if not time_col or not acct_col or not agent_col or not client_col:
        return _pd.DataFrame(), _pd.DataFrame(), 0, 0

    # Parse datetime/time
    dfw[time_col] = _pd.to_datetime(dfw[time_col], errors='coerce')
    dfw[acct_col] = dfw[acct_col].astype(str).str.strip()
    dfw[agent_col] = dfw[agent_col].astype(str).str.strip().str.upper()
    dfw[client_col] = dfw[client_col].astype(str).str.strip().str.upper()

    # Filter clients
    dfw = dfw[dfw[client_col].isin(['EIB', 'ENBD'])]
    dfw = dfw.dropna(subset=[acct_col, agent_col, time_col])

    # Keep latest per Account|Agent
    dfw['__key'] = dfw[acct_col].astype(str) + '|' + dfw[agent_col].astype(str)
    dfw = dfw.sort_values(time_col)
    latest = dfw.groupby('__key', as_index=False).last()

    # extract time
    latest['__t'] = latest[time_col].dt.time

    def in_first(t):
        return t >= _time(12, 0) and t <= _time(17, 0)

    def in_second(t):
        return t > _time(17, 0) and t <= _time(23, 59, 59)

    first = latest[latest['__t'].apply(in_first)][[acct_col, agent_col]].rename(
        columns={acct_col: 'Account', agent_col: 'Agent'}
    ).reset_index(drop=True)

    second = latest[latest['__t'].apply(in_second)][[acct_col, agent_col]].rename(
        columns={acct_col: 'Account', agent_col: 'Agent'}
    ).reset_index(drop=True)

    total_first = len(first)
    total_second = len(second)

    return first, second, total_first, total_second


# ────────────────────────────────────────────────────────────────────────────────────

def calculate_woa_per_agent(df, time_col=None, agent_col=None, client_col=None):
    """
    Calculate WOA counts per agent for each time range.
    Agent code comes from REMARK BY column.
    Returns a DataFrame with AGENT_USER (from REMARK BY), TOTAL_WOA (5pm), and TOTAL_WOA (9pm).
    """
    from datetime import time as _time
    
    if df is None or df.empty:
        return pd.DataFrame(columns=['AGENT_USER', 'TOTAL_WOA (5pm)', 'TOTAL_WOA (9pm)'])
    
    dfw = df.copy()
    
    # Auto-detect columns if not provided
    cols_upper = {c: c.upper() for c in dfw.columns}
    if time_col is None:
        time_col = next((c for c, cu in cols_upper.items() if 'TIME' in cu or 'TIMESTAMP' in cu), None)
    
    # For agent_col, prioritize REMARK BY over other columns
    if agent_col is None:
        agent_col = next((c for c, cu in cols_upper.items() if cu in ('REMARK BY', 'REMARKBY')), None)
        if agent_col is None:
            agent_col = next((c for c, cu in cols_upper.items() if 'AGENT' in cu), None)
    
    if client_col is None:
        client_col = next((c for c, cu in cols_upper.items() if 'CLIENT' in cu), None)
    
    if not time_col or not agent_col:
        return pd.DataFrame(columns=['AGENT_USER', 'TOTAL_WOA (5pm)', 'TOTAL_WOA (9pm)'])
    
    # Parse datetime
    dfw[time_col] = pd.to_datetime(dfw[time_col], errors='coerce')
    dfw[agent_col] = dfw[agent_col].astype(str).str.strip().str.upper()
    
    # Filter by client if available
    if client_col:
        dfw[client_col] = dfw[client_col].astype(str).str.strip().str.upper()
        dfw = dfw[dfw[client_col].isin(['EIB', 'ENBD'])]
    
    dfw = dfw.dropna(subset=[agent_col, time_col])
    
    # Extract time component
    dfw['__t'] = dfw[time_col].dt.time
    
    # Define ranges
    def in_5pm(t):
        return t >= _time(12, 0) and t <= _time(17, 0)
    
    def in_9pm(t):
        return t > _time(17, 0) and t <= _time(23, 59, 59)
    
    dfw['__in_5pm'] = dfw['__t'].apply(in_5pm).astype(int)
    dfw['__in_9pm'] = dfw['__t'].apply(in_9pm).astype(int)
    
    # Group by agent and sum WOA counts
    result = dfw.groupby(agent_col, as_index=False).agg({
        '__in_5pm': 'sum',
        '__in_9pm': 'sum'
    }).rename(columns={
        agent_col: 'AGENT_USER',
        '__in_5pm': 'TOTAL_WOA (5pm)',
        '__in_9pm': 'TOTAL_WOA (9pm)'
    })
    
    return result


# ────────────────────────────────────────────────────────────────────────────────────

def count_accounts_per_agent(df, 
                            account_col='Account',
                            status_col='Status',
                            agent_col=None,
                            amount_col='Amount'):
    """
    Count unique accounts per agent based on status categories.
    Equivalent to VBA CountAccountsPerAgent_NoColOCondition.
    
    Returns: DataFrame with AGENT_USER, TOTAL_WOA (all), POSITIVE (Q), RPC (R), NEGATIVE (S)
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['AGENT_USER', 'TOTAL_WOA', 'POSITIVE', 'RPC', 'NEGATIVE'])
    
    dff = df.copy()
    
    # Auto-detect agent column if not provided
    if agent_col is None:
        cols_upper = {c: c.upper() for c in dff.columns}
        agent_col = next((c for c, cu in cols_upper.items() if cu in ('REMARK BY', 'REMARKBY')), None)
        if agent_col is None:
            agent_col = next((c for c, cu in cols_upper.items() if 'AGENT' in cu), None)
    
    # Auto-detect status and account columns
    cols_upper = {c: c.upper() for c in dff.columns}
    if status_col not in dff.columns:
        status_col = next((c for c, cu in cols_upper.items() if 'STATUS' in cu), None)
    if account_col not in dff.columns:
        account_col = next((c for c, cu in cols_upper.items() if 'ACCOUNT' in cu or 'ACCT' in cu), None)
    if amount_col not in dff.columns:
        amount_col = next((c for c, cu in cols_upper.items() if 'AMOUNT' in cu), None)
    
    if not agent_col or not account_col or not status_col:
        return pd.DataFrame(columns=['AGENT_USER', 'TOTAL_WOA', 'POSITIVE', 'RPC', 'NEGATIVE'])
    
    # Normalize columns
    dff[agent_col] = dff[agent_col].astype(str).str.strip().str.upper()
    dff[account_col] = dff[account_col].astype(str).str.strip()
    dff[status_col] = dff[status_col].astype(str).str.strip().str.upper()
    
    def _clean_numeric_series(s):
        ss = s.fillna('').astype(str).str.strip()
        # remove commas, currency symbols, parentheses and any non-numeric except dot and minus
        ss = ss.str.replace(r'[^0-9\.\-]', '', regex=True)
        ss = ss.replace('', '0')
        return pd.to_numeric(ss, errors='coerce').fillna(0)

    if amount_col:
        dff[amount_col] = _clean_numeric_series(dff[amount_col])
    else:
        dff['__amount'] = 0
        amount_col = '__amount'
    
    # Group by agent
    result = []
    for agent in dff[agent_col].unique():
        if not agent or agent == '':
            continue
        
        agent_data = dff[dff[agent_col] == agent]
        
        # P: All unique accounts
        p_accounts = agent_data[account_col].unique()
        p_count = len(p_accounts)
        
        # Q: Status in STATUS_POSITIVE AND amount <= 1
        q_data = agent_data[
            (agent_data[status_col].isin([s.upper() for s in STATUS_POSITIVE])) &
            (agent_data[amount_col] <= 1)
        ]
        q_count = len(q_data[account_col].unique())
        
        # R: Status in STATUS_RPC
        r_data = agent_data[
            agent_data[status_col].isin([s.upper() for s in STATUS_RPC])
        ]
        r_count = len(r_data[account_col].unique())
        
        # S: Status in STATUS_NEGATIVE
        s_data = agent_data[
            agent_data[status_col].isin([s.upper() for s in STATUS_NEGATIVE])
        ]
        s_count = len(s_data[account_col].unique())
        
        result.append({
            'AGENT_USER': agent,
            'TOTAL_WOA': p_count,      # P = all unique accounts
            'POSITIVE': q_count,        # Q = positive status + amt <= 1
            'RPC': r_count,            # R = RPC status
            'NEGATIVE': s_count        # S = negative status
        })
    
    return pd.DataFrame(result)


# ────────────────────────────────────────────────────────────────────────────────────

def get_ptp_and_payment_data(df, ref_col=None):
    """
    Filter PTP (Promise To Pay) and Payment records per agent.
    
    Criteria (from VBA):
    - Status starts with PTP_* or PAYMENT_* (case-insensitive)
    - Exclude rows with FOLLOW UP, CLAIM PAID, or FULLY PAID in status
    - Exclude rows where amount columns (V=22, Y=25 in VBA) are both 0
    - Extract agent from REMARK BY column
    - Return counts and aggregated data per AGENT_USER
    """
    if df.empty:
        return pd.DataFrame()
    
    df_copy = df.copy()
    
    # Find status column (case-insensitive)
    status_col = None
    for col in df_copy.columns:
        if col.strip().upper() in ("Status",):
            status_col = col
            break
    
    if status_col is None:
        return pd.DataFrame()
    
    # Find agent column - prioritize REMARK BY
    agent_col = None
    for col in df_copy.columns:
        if col.strip().upper() in ("REMARK BY", "REMARKBY"):
            agent_col = col
            break
    
    if agent_col is None:
        return pd.DataFrame()
    
    # Find amount columns (look for various patterns)
    amount_cols = []
    for col in df_copy.columns:
        col_upper = col.strip().upper()
        if 'PTP AMOUNT' in col_upper or 'AMT' in col_upper or 'PAYMENT' in col_upper:
            amount_cols.append(col)

    # If a REF column/df is provided, attempt to extract status lists similar to the Excel REF ranges
    ptp_partial_list = None
    payment_partial_list = None
    ptp_settlement_list = None
    payment_settlement_list = None
    if ref_col is not None:
        # ref_col may be a DataFrame (sheet) or a Series; prefer second column if available
        try:
            if isinstance(ref_col, pd.DataFrame):
                ref_series = ref_col.iloc[:, 1] if ref_col.shape[1] > 1 else ref_col.iloc[:, 0]
            else:
                ref_series = ref_col

            ref_series = ref_series.fillna('').astype(str).str.strip()
            # Excel formulas referenced B33:B38, B39:B41, B42:B43, B44 (1-based)
            if len(ref_series) >= 44:
                ptp_partial_list = ref_series.iloc[32:38].str.upper().str.strip().tolist()
                payment_partial_list = ref_series.iloc[38:41].str.upper().str.strip().tolist()
                ptp_settlement_list = ref_series.iloc[41:43].str.upper().str.strip().tolist()
                payment_settlement_list = [ref_series.iloc[43].upper().strip()]
                # filter out empty strings
                ptp_partial_list = [s for s in ptp_partial_list if s]
                payment_partial_list = [s for s in payment_partial_list if s]
                ptp_settlement_list = [s for s in ptp_settlement_list if s]
                payment_settlement_list = [s for s in payment_settlement_list if s]
        except Exception:
            pass
    
    # Make status uppercase for filtering
    df_copy[status_col] = df_copy[status_col].astype(str).str.upper().str.strip()
    
    # Filter 1: Status starts with PTP or PAYMENT OR matches REF lists when provided
    ptp_payment_mask = (
        df_copy[status_col].str.contains('^PTP', regex=True, na=False) |
        df_copy[status_col].str.contains('^PAYMENT', regex=True, na=False)
    )
    if ptp_partial_list or payment_partial_list or ptp_settlement_list or payment_settlement_list:
        status_vals = df_copy[status_col]
        match_mask = pd.Series([False] * len(df_copy))
        if ptp_partial_list:
            match_mask = match_mask | status_vals.isin(ptp_partial_list)
        if payment_partial_list:
            match_mask = match_mask | status_vals.isin(payment_partial_list)
        if ptp_settlement_list:
            match_mask = match_mask | status_vals.isin(ptp_settlement_list)
        if payment_settlement_list:
            match_mask = match_mask | status_vals.isin(payment_settlement_list)
        ptp_payment_mask = ptp_payment_mask | match_mask
    
    # Filter 2: Exclude FOLLOW UP, CLAIM PAID, FULLY PAID
    exclude_mask = (
        df_copy[status_col].str.contains('FOLLOW UP', na=False) |
        df_copy[status_col].str.contains('CLAIM PAID', na=False) |
        df_copy[status_col].str.contains('FULLY PAID', na=False)
    )
    
    # Filter 3: Not both amount columns are 0
    amount_both_zero = pd.Series([False] * len(df_copy))

    def _clean_numeric_series_local(s):
        ss = s.fillna('').astype(str).str.strip()
        ss = ss.str.replace(r'[^0-9\.\-]', '', regex=True)
        ss = ss.replace('', '0')
        return pd.to_numeric(ss, errors='coerce').fillna(0)

    if len(amount_cols) >= 2:
        # Check if both first two amount columns are 0 (sanitize strings like '1,000.00')
        col1, col2 = amount_cols[0], amount_cols[1]
        num1 = _clean_numeric_series_local(df_copy[col1])
        num2 = _clean_numeric_series_local(df_copy[col2])
        amount_both_zero = (num1 == 0) & (num2 == 0)
    
    # Apply all filters
    df_filtered = df_copy[ptp_payment_mask & ~exclude_mask & ~amount_both_zero].copy()
    
    if df_filtered.empty:
        return pd.DataFrame()
    
    # Extract agent from REMARK BY
    df_filtered["AGENT_USER"] = df_filtered[agent_col].astype(str).str.strip().str.upper()
    
    # Map to known agents
    df_filtered["AGENT_NAME"] = df_filtered["AGENT_USER"].map(AGENT_USER_TO_NAME)
    
    # Filter to only known agents
    df_filtered = df_filtered[df_filtered["AGENT_NAME"].notna()].copy()
    
    if df_filtered.empty:
        return pd.DataFrame()
    
    # Find account/debit number column
    account_col = None
    for col in df_filtered.columns:
        col_upper = col.strip().upper()
        if col_upper in ('ACCOUNT', 'DEBIT NUMBER', 'DEBIT NO', 'ACCT NO', 'ACCOUNT NO.'):
            account_col = col
            break
    
    # Identify amount columns for PTP vs Payment (fallback to first/second found)
    ptp_amt_col = amount_cols[0] if len(amount_cols) >= 1 else None
    payment_amt_col = amount_cols[1] if len(amount_cols) >= 2 else (amount_cols[0] if amount_cols else None)

    # Aggregate by agent
    result = []
    for agent in df_filtered["AGENT_USER"].unique():
        agent_data = df_filtered[df_filtered["AGENT_USER"] == agent]
        

        
        # Sum amounts if amount columns exist (sanitize strings like '1,000.00')
        total_amount = 0
        if amount_cols:
            for col in amount_cols[:2]:  # Use first two amount columns like VBA
                total_amount += _clean_numeric_series_local(agent_data[col]).sum()

        # Calculate partial vs settlement breakdown using REF lists when available
        ptp_partial_amt = 0
        ptp_partial_count = 0
        payment_partial_amt = 0
        payment_partial_count = 0

        ptp_settlement_amt = 0
        ptp_settlement_count = 0
        payment_settlement_amt = 0
        payment_settlement_count = 0

        if ptp_partial_list and ptp_amt_col:
            mask = agent_data[status_col].isin(ptp_partial_list)
            ptp_partial_amt = _clean_numeric_series_local(agent_data.loc[mask, ptp_amt_col]).sum()
            ptp_partial_count = len(agent_data.loc[mask, account_col].unique()) if account_col else int(mask.sum())

        if payment_partial_list and payment_amt_col:
            mask = agent_data[status_col].isin(payment_partial_list)
            payment_partial_amt = _clean_numeric_series_local(agent_data.loc[mask, payment_amt_col]).sum()
            payment_partial_count = len(agent_data.loc[mask, account_col].unique()) if account_col else int(mask.sum())

        if ptp_settlement_list and ptp_amt_col:
            mask = agent_data[status_col].isin(ptp_settlement_list)
            ptp_settlement_amt = _clean_numeric_series_local(agent_data.loc[mask, ptp_amt_col]).sum()
            ptp_settlement_count = len(agent_data.loc[mask, account_col].unique()) if account_col else int(mask.sum())

        if payment_settlement_list and payment_amt_col:
            mask = agent_data[status_col].isin(payment_settlement_list)
            payment_settlement_amt = _clean_numeric_series_local(agent_data.loc[mask, payment_amt_col]).sum()
            payment_settlement_count = len(agent_data.loc[mask, account_col].unique()) if account_col else int(mask.sum())
        
        result.append({
            'AGENT_USER': agent,
            'AGENT_NAME': agent_data["AGENT_NAME"].iloc[0],
            'PTP_PARTIAL_COUNT': ptp_partial_count,
            'PTP_PARTIAL_AMOUNT': ptp_partial_amt,
            'PAYMENT_PARTIAL_COUNT': payment_partial_count,
            'PAYMENT_PARTIAL_AMOUNT': payment_partial_amt,
            'PTP_SETTLEMENT_COUNT': ptp_settlement_count,
            'PTP_SETTLEMENT_AMOUNT': ptp_settlement_amt,
            'PAYMENT_SETTLEMENT_COUNT': payment_settlement_count,
            'PAYMENT_SETTLEMENT_AMOUNT': payment_settlement_amt
        })
    
    return pd.DataFrame(result)


# ┌─────────────────────────────────────────────────────────────────────────────────┐
# │                  UI DISPLAY FUNCTIONS                         │
# └─────────────────────────────────────────────────────────────────────────────────┘

def get_default_data_for_client(client_name, start_date):
    """Return a default dataframe for the given client with agent names and zeroed metrics."""
    if client_name == "ENBD":
        agents = [
            ("Niecel Escopalao", "NCESCOPALAO"),
            ("Henry Paolo P. Bonabon", "HPBONABON"),
            ("John Vincent Ortega", "JTORTEGA"),
            ("Cheska Mare Medalla", "CGMEDALLA"),
            ("Christian Jeric Lajera Camado", "CLCAMADO"),
            ("James Eduard Q. Cayno", "JCAYNO"),
            ("Gearbey M. Cuenca", "GCUENCA"),
            ("John Mark D. Paculaba", "JPACULABA")
        ]
    else:  # EIB
        agents = [
            ("Dorithy Gail Cajes", "DECAJES"),
            ("Kimberly Dulosa", "DECAJES"),
            ("Samantha Nicole B. Canales", "SBCANALES")
        ]

    rows = []
    for name, user in agents:
        rows.append({
            "AGENT_NAME": name,
            "AGENT_USER": user,
            "TOTAL_WOA (5pm)": 0,
            "TOTAL_WOA (9pm)": 0,
            "TOTAL_WOA": 0,
            "NEGATIVE": 0,
            "RPC": 0,
            "POSITIVE": 0,
            "TOTAL_PTP_COUNT": 0,
            "TOTAL_PAYMENT_COUNT": 0,
            "PTP_PAYMENT_COUNT": 0,
            "PTP_PAYMENT_AMOUNT": 0,
            "SETTLEMENT_COUNT": 0,
            "SETTLEMENT_AMOUNT": 0,
            "PTP_PARTIAL_COUNT": 0,
            "PTP_PARTIAL_AMOUNT": 0,
            "PAYMENT_PARTIAL_COUNT": 0,
            "PAYMENT_PARTIAL_AMOUNT": 0,
            "PTP_SETTLEMENT_COUNT": 0,
            "PTP_SETTLEMENT_AMOUNT": 0,
            "PAYMENT_SETTLEMENT_COUNT": 0,
            "PAYMENT_SETTLEMENT_AMOUNT": 0,
            "TOTAL_TALK_TIME": 0,
            "PTP_PERCENTAGE": "0%",
            "NEW_RPC": 0,
            "NEW_IDP_ACTIVE": 0,
            "GRACE_PERCENTAGE": "0%",
            "START_DATE": start_date
        })

    return pd.DataFrame(rows)


# ────────────────────────────────────────────────────────────────────────────────────

def display_dashboard(client_name):
    """Render professional dashboard for ENBD/EIB"""
    # Use per-client payment_data and ptp_data from session state
    payment_data = st.session_state.get(f"{client_name}_payment_data", pd.DataFrame())
    ptp_data = st.session_state.get(f"{client_name}_ptp_data", pd.DataFrame())
    
    # Header
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>{client_name} PIPELINE</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # === DATE SELECTOR ===
    col_selector, col_spacer = st.columns([2, 4])
    with col_selector:
        date_selection_type = st.radio(
            "📅 Select Date Range",
            ["Specific Date", "By Month", "By Year"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if date_selection_type == "Specific Date":
            selected_date = st.date_input(
                "📅 Select Specific Date",
                value=st.session_state.start_date,
                help="Choose a specific date"
            )
        elif date_selection_type == "By Month":
            col_year, col_month = st.columns(2)
            with col_year:
                year = st.number_input(
                    "Year",
                    min_value=2020,
                    max_value=2030,
                    value=st.session_state.start_date.year,
                    key="disp_year"
                )
            with col_month:
                month = st.selectbox(
                    "Month",
                    list(range(1, 13)),
                    format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
                    index=st.session_state.start_date.month - 1,
                    key="disp_month"
                )
            # Set to first day of selected month
            selected_date = datetime.date(year, month, 1)
        else:  # By Year
            year = st.number_input(
                "📅 Select Year",
                min_value=2020,
                max_value=2030,
                value=st.session_state.start_date.year,
                key="disp_year_only"
            )
            # Set to first day of selected year
            selected_date = datetime.date(year, 1, 1)
        
        if selected_date != st.session_state.start_date:
            st.session_state.start_date = selected_date
            st.rerun()
    
    st.markdown("---")
    
    # === TOP METRICS ===
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate totals from DATE-based columns if they exist
    total_posted_aed = 0
    total_ptp_amount = 0
    total_collections_count = 0
    total_ptp_count = 0
    
    # Filter payment data by date
    filtered_payment = payment_data.copy()
    filtered_ptp = ptp_data.copy()
    
    if not filtered_payment.empty and "DATE" in filtered_payment.columns:
        filtered_payment["DATE"] = pd.to_datetime(filtered_payment["DATE"], errors='coerce')
        selected_dt = pd.Timestamp(st.session_state.start_date)
        
        if date_selection_type == "Specific Date":
            filtered_payment = filtered_payment[filtered_payment["DATE"].dt.date == st.session_state.start_date]
        elif date_selection_type == "By Month":
            filtered_payment = filtered_payment[
                (filtered_payment["DATE"].dt.year == selected_dt.year) &
                (filtered_payment["DATE"].dt.month == selected_dt.month)
            ]
        else:  # By Year
            filtered_payment = filtered_payment[filtered_payment["DATE"].dt.year == selected_dt.year]
    
    if not filtered_ptp.empty and "DATE" in filtered_ptp.columns:
        filtered_ptp["DATE"] = pd.to_datetime(filtered_ptp["DATE"], errors='coerce')
        selected_dt = pd.Timestamp(st.session_state.start_date)
        
        if date_selection_type == "Specific Date":
            filtered_ptp = filtered_ptp[filtered_ptp["DATE"].dt.date == st.session_state.start_date]
        elif date_selection_type == "By Month":
            filtered_ptp = filtered_ptp[
                (filtered_ptp["DATE"].dt.year == selected_dt.year) &
                (filtered_ptp["DATE"].dt.month == selected_dt.month)
            ]
        else:  # By Year
            filtered_ptp = filtered_ptp[filtered_ptp["DATE"].dt.year == selected_dt.year]
    
    # Calculate totals
    if "POSTED AED" in filtered_payment.columns:
        total_posted_aed = pd.to_numeric(filtered_payment["POSTED AED"], errors='coerce').sum()
        total_collections_count = len(filtered_payment[filtered_payment["POSTED AED"].notna()])
    
    if "PTP AMOUNT" in filtered_ptp.columns:
        total_ptp_amount = pd.to_numeric(filtered_ptp["PTP AMOUNT"], errors='coerce').sum()
        total_ptp_count = len(filtered_ptp[filtered_ptp["PTP AMOUNT"].notna()])
    
    with col1:
        st.metric("💰 TOTAL COLLECTIONS (AED)", f"AED {total_posted_aed:,.4f}", help="Posted AED")
    
    with col2:
        st.metric("📊 PTP PROJECTION (AED)", f"AED {total_ptp_amount:,.2f}", help="PTP Amount")
    
    with col3:
        st.metric("📁 TOTAL COLLECTIONS", int(total_collections_count))
    
    with col4:
        st.metric("📈 PTP PROJECTION", int(total_ptp_count))
    
    st.markdown("---")
    
    # === COLLECTION VS TARGET SECTION ===
    col_target1, col_target2 = st.columns(2)
    
    with col_target1:
        st.subheader("📊 COLLECTION VS TARGET")
        
        # Get target value from per-client target_data based on selected date
        target_value = 100000  # Default
        target_data = st.session_state.get(f"{client_name}_target_data", pd.DataFrame())
        
        if not target_data.empty:
            # Ensure Year and Month are numeric
            target_data = target_data.copy()
            target_data['Year'] = pd.to_numeric(target_data['Year'], errors='coerce')
            target_data['Month'] = pd.to_numeric(target_data['Month'], errors='coerce')
            target_data['Target AED'] = pd.to_numeric(target_data['Target AED'], errors='coerce')
            
            current_year = st.session_state.start_date.year
            current_month = st.session_state.start_date.month
            
            if date_selection_type == "Specific Date" or date_selection_type == "By Month":
                # Find target for this year and month
                matching_target = target_data[
                    (target_data['Year'] == current_year) &
                    (target_data['Month'] == current_month)
                ]
                if not matching_target.empty:
                    target_value = float(matching_target.iloc[0]['Target AED'])
            elif date_selection_type == "By Year":
                # Average targets for the year
                year_targets = target_data[target_data['Year'] == current_year]
                if not year_targets.empty:
                    target_value = float(year_targets['Target AED'].mean())
        
        # Create gauge chart comparing total collections vs target
        fig_gauge = go.Figure(data=[go.Indicator(
            mode="gauge+number",
            value=total_posted_aed,
            title={'text': f"Collections vs Target (AED {target_value:,.0f})"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, target_value]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, target_value * 0.5], 'color': "lightgray"},
                    {'range': [target_value * 0.5, target_value], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target_value
                }
            }
        )])
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Show target info
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("Current Target", f"AED {target_value:,.0f}")
        with col_info2:
            st.metric("Total Collections", f"AED {total_posted_aed:,.2f}")
        with col_info3:
            if target_value > 0:
                progress = (total_posted_aed / target_value) * 100
                st.metric("Progress", f"{progress:.1f}%")
            else:
                st.metric("Progress", "N/A")
    
    with col_target2:
        st.subheader("📈 CONVERTED PTP")
        # Bar chart showing PTP vs Payment conversion
        conversion_data = {
            'Type': ['PTP PROJECTION', 'TOTAL COLLECTIONS'],
            'Amount (AED)': [total_ptp_amount, total_posted_aed]
        }
        fig_conversion = px.bar(conversion_data, x='Type', y='Amount (AED)', 
                               color='Type', 
                               color_discrete_sequence=['#3498db', '#2ecc71'])
        st.plotly_chart(fig_conversion, use_container_width=True)
    
    st.markdown("---")
    
    # === CHARTS SECTION ===
    col_payment_chart, col_ptp_chart = st.columns(2)
    
    with col_payment_chart:
        st.subheader("💳 PAYMENT - POSTED AED")
        # Group by DATE and sum POSTED AED
        if "DATE" in filtered_payment.columns and "POSTED AED" in filtered_payment.columns and not filtered_payment.empty:
            data_copy = filtered_payment.copy()
            data_copy["DATE"] = pd.to_datetime(data_copy["DATE"], errors='coerce')
            payment_by_date = data_copy.groupby(data_copy["DATE"].dt.date)["POSTED AED"].apply(
                lambda x: pd.to_numeric(x, errors='coerce').sum()
            ).reset_index()
            payment_by_date.columns = ["DATE", "POSTED AED"]
            
            fig_payment = px.line(payment_by_date, x='DATE', y='POSTED AED',
                                 markers=True, title="Payment Posted AED by Date")
            fig_payment.update_traces(line=dict(color='#2ecc71', width=2))
            st.plotly_chart(fig_payment, use_container_width=True)
        else:
            st.info("📊 No payment data available")
    
    with col_ptp_chart:
        st.subheader("📋 PTP PROJECTION - PTP AMOUNT")
        # Group by DATE and sum PTP AMOUNT
        if "DATE" in filtered_ptp.columns and "PTP AMOUNT" in filtered_ptp.columns and not filtered_ptp.empty:
            data_copy = filtered_ptp.copy()
            data_copy["DATE"] = pd.to_datetime(data_copy["DATE"], errors='coerce')
            ptp_by_date = data_copy.groupby(data_copy["DATE"].dt.date)["PTP AMOUNT"].apply(
                lambda x: pd.to_numeric(x, errors='coerce').sum()
            ).reset_index()
            ptp_by_date.columns = ["DATE", "PTP AMOUNT"]
            
            fig_ptp = px.line(ptp_by_date, x='DATE', y='PTP AMOUNT',
                             markers=True, title="PTP Amount by Date")
            fig_ptp.update_traces(line=dict(color='#3498db', width=2))
            st.plotly_chart(fig_ptp, use_container_width=True)
        else:
            st.info("📊 No PTP data available")
    
    st.markdown("---")


# ┌─────────────────────────────────────────────────────────────────────────────────┐
# │              DATA MANAGEMENT TAB FUNCTIONS                    │
# └─────────────────────────────────────────────────────────────────────────────────┘

def payment_monitoring_tab_enbd(client_name="ENBD"):
    """Payment monitoring sheet (read-only grid; add/delete only)"""
    st.subheader(f"💳 {client_name} - Payment Monitoring Sheet")
    st.info("📌 Data is grouped by **DATE** column. **POSTED AED** values are summed per date for Payment charts")

    # Use client-specific session state keys
    session_key = f"{client_name}_payment_data"

    # Initialize payment data in session state if not exists
    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame({
            'AGREEMENT NO': [],
            'AGREEMENT ID': [],
            'CIF NO': [],
            'RELATIONSHIP NO': [],
            'TOUCHED POINTS': [],
            'OFFICIAL AGENT': [],
            'CM NAME': [],
            'PRODUCTS CAT': [],
            'VINTAGE': [],
            'PAYMENT STATUS': [],
            'DATE': [],
            'POSTED AED': [],
            'POSTED PH': [],
            'CF %': [],
            'CF AMT': [],
            'MONTH': []
        })

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Manage payment records (read-only grid).**")

    # Add Details form in an expander (compact 3-column layout)
    with st.expander("➕ Add Details"):
        with st.form(f"add_payment_details_{client_name}"):
            new_vals = {}
            form_key_base = f"add_payment_{client_name}"
            cols_input = st.columns(3)
            for i, col in enumerate(st.session_state[session_key].columns):
                c = cols_input[i % 3]
                key = (f"{form_key_base}_{col}").replace(' ', '_')
                new_vals[col] = c.text_input(col, key=key)
            submitted = st.form_submit_button("Add Record")
            if submitted:
                new_row = {col: new_vals.get(col, '') for col in st.session_state[session_key].columns}
                # default MONTH if present
                if 'MONTH' in new_row and not new_row['MONTH']:
                    new_row['MONTH'] = st.session_state.start_date.strftime('%Y-%m')
                st.session_state[session_key] = pd.concat(
                    [st.session_state[session_key], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.success("✓ Record added")
                st.rerun()

    # Display read-only grid
    st.dataframe(st.session_state[session_key], use_container_width=True, height=500)

    # Deletion controls
    if not st.session_state[session_key].empty:
        # Build human-friendly labels for rows
        def _row_label(i, row):
            label_field = None
            for cand in ['AGREEMENT NO', 'AGREEMENT ID', 'AGREEMENT', 'CIF NO']:
                if cand in st.session_state[session_key].columns:
                    label_field = cand
                    break
            label_val = str(row[label_field]) if label_field else str(i)
            return f"{i} - {label_val}"

        options = [_row_label(i, st.session_state[session_key].iloc[i]) for i in range(len(st.session_state[session_key]))]
        to_delete = st.multiselect("Select rows to delete", options, key=f"delete_payment_rows_{client_name}")
        if st.button("🗑️ Delete Selected", key=f"delete_payment_btn_{client_name}"):
            if to_delete:
                # parse indices and drop
                indices = [int(x.split(' - ')[0]) for x in to_delete]
                st.session_state[session_key] = st.session_state[session_key].drop(index=indices).reset_index(drop=True)
                st.success(f"✓ Deleted {len(indices)} row(s)")
                st.rerun()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download Payment Data", key=f"download_payment_{client_name}"):
            csv = st.session_state[session_key].to_csv(index=False)
            st.download_button(
                label="CSV File",
                data=csv,
                file_name=f"{client_name}_payment_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        st.metric("Total Records", len(st.session_state[session_key]))
    
    with col3:
        try:
            total_posted_aed = pd.to_numeric(st.session_state[session_key]['POSTED AED'], errors='coerce').sum()
            st.metric("Total Posted AED", f"AED {total_posted_aed:,.2f}")
        except:
            st.metric("Total Posted AED", "AED 0.00")

def payment_monitoring_tab_eib(client_name="EIB"):
    """Payment monitoring sheet (read-only grid; add/delete only)"""
    st.subheader(f"💳 {client_name} - Payment Monitoring Sheet")
    st.info("📌 Data is grouped by **DATE** column. **POSTED AED** values are summed per date for Payment charts")

    # Use client-specific session state keys
    session_key = f"{client_name}_payment_data"

    # Initialize payment data in session state if not exists
    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame({
            'AGREEMENT NO': [],
            'AGREEMENT ID': [],
            'CIF NO': [],
            'RELATIONSHIP NO': [],
            'TOUCHED POINTS': [],
            'OFFICIAL AGENT': [],
            'CM NAME': [],
            'PRODUCTS CAT': [],
            'VINTAGE': [],
            'PAYMENT STATUS': [],
            'DATE': [],
            'POSTED AED': [],
            'POSTED PH': [],
            'CF %': [],
            'CF AMT': [],
            'MONTH': []
        })

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Manage payment records (read-only grid).**")

    # Add Details form in an expander (compact 3-column layout)
    with st.expander("➕ Add Details"):
        with st.form(f"add_payment_details_{client_name}"):
            new_vals = {}
            form_key_base = f"add_payment_{client_name}"
            cols_input = st.columns(3)
            for i, col in enumerate(st.session_state[session_key].columns):
                c = cols_input[i % 3]
                key = (f"{form_key_base}_{col}").replace(' ', '_')
                new_vals[col] = c.text_input(col, key=key)
            submitted = st.form_submit_button("Add Record")
            if submitted:
                new_row = {col: new_vals.get(col, '') for col in st.session_state[session_key].columns}
                # default MONTH if present
                if 'MONTH' in new_row and not new_row['MONTH']:
                    new_row['MONTH'] = st.session_state.start_date.strftime('%Y-%m')
                st.session_state[session_key] = pd.concat(
                    [st.session_state[session_key], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.success("✓ Record added")
                st.rerun()

    # Display read-only grid
    st.dataframe(st.session_state[session_key], use_container_width=True, height=500)

    # Deletion controls
    if not st.session_state[session_key].empty:
        # Build human-friendly labels for rows
        def _row_label(i, row):
            label_field = None
            for cand in ['AGREEMENT NO', 'AGREEMENT ID', 'AGREEMENT', 'CIF NO']:
                if cand in st.session_state[session_key].columns:
                    label_field = cand
                    break
            label_val = str(row[label_field]) if label_field else str(i)
            return f"{i} - {label_val}"

        options = [_row_label(i, st.session_state[session_key].iloc[i]) for i in range(len(st.session_state[session_key]))]
        to_delete = st.multiselect("Select rows to delete", options, key=f"delete_payment_rows_{client_name}")
        if st.button("🗑️ Delete Selected", key=f"delete_payment_btn_{client_name}"):
            if to_delete:
                # parse indices and drop
                indices = [int(x.split(' - ')[0]) for x in to_delete]
                st.session_state[session_key] = st.session_state[session_key].drop(index=indices).reset_index(drop=True)
                st.success(f"✓ Deleted {len(indices)} row(s)")
                st.rerun()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download Payment Data", key=f"download_payment_{client_name}"):
            csv = st.session_state[session_key].to_csv(index=False)
            st.download_button(
                label="CSV File",
                data=csv,
                file_name=f"{client_name}_payment_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        st.metric("Total Records", len(st.session_state[session_key]))
    
    with col3:
        try:
            total_posted_aed = pd.to_numeric(st.session_state[session_key]['POSTED AED'], errors='coerce').sum()
            st.metric("Total Posted AED", f"AED {total_posted_aed:,.2f}")
        except:
            st.metric("Total Posted AED", "AED 0.00")

# ────────────────────────────────────────────────────────────────────────────────────

def ptp_list_tab_enbd(client_name="ENBD"):
    """Editable PTP list sheet"""
    st.subheader(f"📋 {client_name} - PTP List Sheet")
    st.info("📌 Data is grouped by **DATE** column. **PTP AMOUNT** values are summed per date for PTP charts")
    
    # Use client-specific session state keys
    session_key = f"{client_name}_ptp_data"
    
    # Initialize PTP data in session state if not exists
    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame({
            'AGREEMENT NO': [],
            'AGREEMENT ID': [],
            'CUSTOMER NO': [],
            'RELATIONSHIP NO': [],
            'AGENT': [],
            'CM NAME': [],
            'PRODUCTS CAT': [],
            'VINTAGE': [],
            'STATUS': [],
            'DATE': [],
            'MONTH': [],
            'PTP AMOUNT': [],
            'STATUS TODAY': [],
            'BROKEN AMOUNT': []
        })
    
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Manage PTP records (read-only grid).**")

    # Add Details form in an expander (compact 3-column layout)
    with st.expander("➕ Add Details"):
        with st.form(f"add_ptp_details_{client_name}"):
            new_vals = {}
            form_key_base = f"add_ptp_{client_name}"
            cols_input = st.columns(3)
            for i, col in enumerate(st.session_state[session_key].columns):
                c = cols_input[i % 3]
                key = (f"{form_key_base}_{col}").replace(' ', '_')
                new_vals[col] = c.text_input(col, key=key)
            submitted = st.form_submit_button("Add Record")
            if submitted:
                new_row = {col: new_vals.get(col, '') for col in st.session_state[session_key].columns}
                if 'MONTH' in new_row and not new_row['MONTH']:
                    new_row['MONTH'] = st.session_state.start_date.strftime('%Y-%m')
                st.session_state[session_key] = pd.concat(
                    [st.session_state[session_key], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.success("✓ Record added")
                st.rerun()

    # Display read-only grid
    st.dataframe(st.session_state[session_key], use_container_width=True, height=500)

    # Deletion controls
    if not st.session_state[session_key].empty:
        def _row_label(i, row):
            label_field = None
            for cand in ['AGREEMENT NO', 'AGREEMENT ID', 'CUSTOMER NO', 'AGREEMENT']:
                if cand in st.session_state[session_key].columns:
                    label_field = cand
                    break
            label_val = str(row[label_field]) if label_field else str(i)
            return f"{i} - {label_val}"

        options = [_row_label(i, st.session_state[session_key].iloc[i]) for i in range(len(st.session_state[session_key]))]
        to_delete = st.multiselect("Select rows to delete", options, key=f"delete_ptp_rows_{client_name}")
        if st.button("🗑️ Delete Selected", key=f"delete_ptp_btn_{client_name}"):
            if to_delete:
                indices = [int(x.split(' - ')[0]) for x in to_delete]
                st.session_state[session_key] = st.session_state[session_key].drop(index=indices).reset_index(drop=True)
                st.success(f"✓ Deleted {len(indices)} row(s)")
                st.rerun()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download PTP Data", key=f"download_ptp_{client_name}"):
            csv = st.session_state[session_key].to_csv(index=False)
            st.download_button(
                label="CSV File",
                data=csv,
                file_name=f"{client_name}_ptp_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        st.metric("Total PTP Records", len(st.session_state[session_key]))
    
    with col3:
        try:
            ptp_amount = pd.to_numeric(st.session_state[session_key]['PTP AMOUNT'], errors='coerce').sum()
            st.metric("Total PTP Amount", f"AED {ptp_amount:,.2f}")
        except:
            st.metric("Total PTP Amount", "AED 0.00")

def ptp_list_tab_eib(client_name="EIB"):
    """Editable PTP list sheet"""
    st.subheader(f"📋 {client_name} - PTP List Sheet")
    st.info("📌 Data is grouped by **DATE** column. **PTP AMOUNT** values are summed per date for PTP charts")
    
    # Use client-specific session state keys
    session_key = f"{client_name}_ptp_data"
    
    # Initialize PTP data in session state if not exists
    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame({
            'AGREEMENT NO': [],
            'AGREEMENT ID': [],
            'CUSTOMER NO': [],
            'RELATIONSHIP NO': [],
            'AGENT': [],
            'CM NAME': [],
            'PRODUCTS CAT': [],
            'VINTAGE': [],
            'STATUS': [],
            'DATE': [],
            'MONTH': [],
            'PTP AMOUNT': [],
            'STATUS TODAY': [],
            'BROKEN AMOUNT': []
        })
    
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Manage PTP records (read-only grid).**")

    # Add Details form in an expander (compact 3-column layout)
    with st.expander("➕ Add Details"):
        with st.form(f"add_ptp_details_{client_name}"):
            new_vals = {}
            form_key_base = f"add_ptp_{client_name}"
            cols_input = st.columns(3)
            for i, col in enumerate(st.session_state[session_key].columns):
                c = cols_input[i % 3]
                key = (f"{form_key_base}_{col}").replace(' ', '_')
                new_vals[col] = c.text_input(col, key=key)
            submitted = st.form_submit_button("Add Record")
            if submitted:
                new_row = {col: new_vals.get(col, '') for col in st.session_state[session_key].columns}
                if 'MONTH' in new_row and not new_row['MONTH']:
                    new_row['MONTH'] = st.session_state.start_date.strftime('%Y-%m')
                st.session_state[session_key] = pd.concat(
                    [st.session_state[session_key], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.success("✓ Record added")
                st.rerun()

    # Display read-only grid
    st.dataframe(st.session_state[session_key], use_container_width=True, height=500)

    # Deletion controls
    if not st.session_state[session_key].empty:
        def _row_label(i, row):
            label_field = None
            for cand in ['AGREEMENT NO', 'AGREEMENT ID', 'CUSTOMER NO', 'AGREEMENT']:
                if cand in st.session_state[session_key].columns:
                    label_field = cand
                    break
            label_val = str(row[label_field]) if label_field else str(i)
            return f"{i} - {label_val}"

        options = [_row_label(i, st.session_state[session_key].iloc[i]) for i in range(len(st.session_state[session_key]))]
        to_delete = st.multiselect("Select rows to delete", options, key=f"delete_ptp_rows_{client_name}")
        if st.button("🗑️ Delete Selected", key=f"delete_ptp_btn_{client_name}"):
            if to_delete:
                indices = [int(x.split(' - ')[0]) for x in to_delete]
                st.session_state[session_key] = st.session_state[session_key].drop(index=indices).reset_index(drop=True)
                st.success(f"✓ Deleted {len(indices)} row(s)")
                st.rerun()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download PTP Data", key=f"download_ptp_{client_name}"):
            csv = st.session_state[session_key].to_csv(index=False)
            st.download_button(
                label="CSV File",
                data=csv,
                file_name=f"{client_name}_ptp_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        st.metric("Total PTP Records", len(st.session_state[session_key]))
    
    with col3:
        try:
            ptp_amount = pd.to_numeric(st.session_state[session_key]['PTP AMOUNT'], errors='coerce').sum()
            st.metric("Total PTP Amount", f"AED {ptp_amount:,.2f}")
        except:
            st.metric("Total PTP Amount", "AED 0.00")
# ────────────────────────────────────────────────────────────────────────────────────

def target_settings_tab(client_name="ENBD"):
    """Target settings management for COLLECTION VS TARGET"""
    st.subheader("🎯 Collection Target Settings")
    st.info("📌 Set monthly and yearly targets for collection comparisons")
    # Client selector for target settings
    client_select = st.selectbox(
        "Client",
        ["ENBD", "EIB"],
        index=0 if client_name in ("", None) or client_name == "ENBD" else 1,
        key="target_client_select"
    )

    # Use per-client session key for targets
    session_key = f"{client_select}_target_data"

    # Initialize target data in session state if not exists for this client
    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame({
            'Year': [],
            'Month': [],
            'Target AED': []
        })
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        target_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2030,
            value=st.session_state.start_date.year,
            key="target_year"
        )
    
    with col2:
        target_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
            index=st.session_state.start_date.month - 1,
            key="target_month"
        )
    
    with col3:
        target_amount = st.number_input(
            "Target Amount (AED)",
            min_value=0,
            value=100000,
            step=1000,
            key="target_amount"
        )
    
    if st.button("➕ Add/Update Target", use_container_width=True):
        # Convert to proper types
        target_year = int(target_year)
        target_month = int(target_month)
        target_amount = float(target_amount)
        
        # Check if target for this year/month already exists
        existing_mask = (
            (st.session_state[session_key]['Year'].astype(int) == target_year) &
            (st.session_state[session_key]['Month'].astype(int) == target_month)
        )
        existing = st.session_state[session_key][existing_mask]
        
        if not existing.empty:
            # Update existing
            st.session_state[session_key].loc[existing_mask, 'Target AED'] = target_amount
            st.success(f"✓ Updated target for {datetime.date(2020, target_month, 1).strftime('%B')} {target_year}")
        else:
            # Add new
            new_target = pd.DataFrame({
                'Year': [target_year],
                'Month': [target_month],
                'Target AED': [target_amount]
            })
            st.session_state[session_key] = pd.concat(
                [st.session_state[session_key], new_target],
                ignore_index=True
            )
            st.success(f"✓ Added target for {datetime.date(2020, target_month, 1).strftime('%B')} {target_year}")
        st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Current Targets")

    if not st.session_state[session_key].empty:
        # Display as editable table
        display_targets = st.session_state[session_key].copy()
        
        # Convert month number to name safely
        def month_to_name(x):
            try:
                month_num = int(x)
                if 1 <= month_num <= 12:
                    return datetime.date(2020, month_num, 1).strftime('%B')
                return "Invalid"
            except:
                return "Invalid"
        
        display_targets['Month Name'] = display_targets['Month'].apply(month_to_name)
        
        edited_targets = st.data_editor(
            display_targets[['Year', 'Month Name', 'Target AED']],
            key=f"targets_data_editor_{client_select}",
            use_container_width=True,
            hide_index=True
        )
        
        # Update session state if changes were made
        if not edited_targets.empty:
            st.session_state[session_key] = display_targets[['Year', 'Month', 'Target AED']].copy()
        
        # Delete targets
        st.markdown("---")
        delete_col1, delete_col2 = st.columns([3, 1])
        with delete_col1:
            st.markdown("**Delete Target:**")
        with delete_col2:
            if st.button("🗑️ Delete Selected", use_container_width=True):
                st.session_state[session_key] = st.session_state[session_key].iloc[0:0]  # Clear all for this client
                st.success("✓ All targets cleared")
                st.rerun()
    else:
        st.info("ℹ️ No targets set yet. Add a target above to get started.")


# ────────────────────────────────────────────────────────────────────────────────────

def admin_data_tab():
    """Admin data management interface"""
    st.header("⚙️ Admin - Data Management")
    
    # Main tabs for different data types
    data_tabs = st.tabs(["Dashboard Data", "ENBD Payment", "EIB Payment", "ENBD PTP", "EIB PTP", "Target Settings"])
    
    with data_tabs[0]:
        dashboard_data_tab()
    
    with data_tabs[1]:
        payment_monitoring_tab_enbd("ENBD")
    
    with data_tabs[2]:
        payment_monitoring_tab_eib("EIB")
    
    with data_tabs[3]:
        ptp_list_tab_enbd("ENBD")
    
    with data_tabs[4]:
        ptp_list_tab_eib("EIB")
    
    with data_tabs[5]:
        target_settings_tab("")


# ────────────────────────────────────────────────────────────────────────────────────

def dashboard_data_tab():
    """Original dashboard data management"""
    col_date, col_type, col_client = st.columns([2, 2, 2])
    
    with col_date:
        date_selection_type = st.radio(
            "Date Range Type",
            ["Specific Date", "By Month", "By Year"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if date_selection_type == "Specific Date":
            st.session_state.start_date = st.date_input(
                "📅 Select START_DATE",
                st.session_state.start_date,
                help="Date only, no time component"
            )
        elif date_selection_type == "By Month":
            col_year, col_month = st.columns(2)
            with col_year:
                year = st.number_input(
                    "Year",
                    min_value=2020,
                    max_value=2030,
                    value=st.session_state.start_date.year,
                    key="date_tab_year"
                )
            with col_month:
                month = st.selectbox(
                    "Month",
                    list(range(1, 13)),
                    format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
                    index=st.session_state.start_date.month - 1,
                    key="date_tab_month"
                )
            st.session_state.start_date = datetime.date(year, month, 1)
        else:  # By Year
            year = st.number_input(
                "📅 Select Year",
                min_value=2020,
                max_value=2030,
                value=st.session_state.start_date.year,
                key="date_tab_year_only"
            )
            st.session_state.start_date = datetime.date(year, 1, 1)
    
    with col_client:
        client_select = st.selectbox(
            "🏢 Select Client",
            ["ENBD", "EIB"]
        )

    # If no data exists yet for the selected client, populate defaults
    if client_select == "ENBD":
        if st.session_state.enbd_data.empty:
            st.session_state.enbd_data = get_default_data_for_client("ENBD", st.session_state.start_date)
    else:
        if st.session_state.eib_data.empty:
            st.session_state.eib_data = get_default_data_for_client("EIB", st.session_state.start_date)
    
    st.markdown("---")
    st.subheader("✏️ Editable Data Grid")
    
    current_data = st.session_state.enbd_data if client_select == "ENBD" else st.session_state.eib_data
    
    # Filter data based on selected date range
    filtered_data = current_data.copy()
    
    # Convert START_DATE to datetime if not already
    if "START_DATE" in filtered_data.columns and not filtered_data.empty:
        filtered_data["START_DATE"] = pd.to_datetime(filtered_data["START_DATE"], errors='coerce')
        selected_dt = pd.Timestamp(st.session_state.start_date)
        
        if date_selection_type == "Specific Date":
            # Filter by exact date
            filtered_data = filtered_data[filtered_data["START_DATE"].dt.date == st.session_state.start_date]
        elif date_selection_type == "By Month":
            # Filter by year and month
            filtered_data = filtered_data[
                (filtered_data["START_DATE"].dt.year == selected_dt.year) &
                (filtered_data["START_DATE"].dt.month == selected_dt.month)
            ]
        else:  # By Year
            # Filter by year only
            filtered_data = filtered_data[filtered_data["START_DATE"].dt.year == selected_dt.year]
    
    current_data = filtered_data
    if not current_data.empty:
        edited_data = st.data_editor(
            current_data,
            key=f"client_data_editor_{client_select}",
            use_container_width=True,
            height=400
        )
        
        if client_select == "ENBD":
            st.session_state.enbd_data = edited_data
        else:
            st.session_state.eib_data = edited_data
        
        st.markdown("---")
        
        # Filter out system and ctbonifacio from export
        export_data = edited_data[
            ~edited_data['AGENT_USER'].astype(str).str.upper().isin(['SYSTEM', 'CTBONIFACIO'])
        ]
        csv_data = export_data.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {client_select} CSV",
            data=csv_data,
            file_name=f"{client_select}_{st.session_state.start_date}.csv",
            mime="text/csv"
        )
    else:
        st.info(f"ℹ️ No data for {client_select}. Upload a file first.")
    
    st.markdown("---")
    st.subheader("📤 Upload MASTERLIST")
    
    uploaded_file = st.file_uploader(
        "Upload Excel or CSV file",
        type=["xlsx", "xls", "csv"],
        help="REMARK BY column will be used as AGENT_NAME"
    )
    
    if uploaded_file is not None:
        try:
            # Read file (capture REF sheet when present)
            ref_df = None
            if uploaded_file.name.endswith(".csv"):
                df_uploaded = pd.read_csv(uploaded_file)
            else:
                sheets = pd.read_excel(uploaded_file, sheet_name=None)
                # pick first non-REF sheet as main data, capture REF if exists
                main_df = None
                for name, sheet in sheets.items():
                    if name.strip().upper() == 'REF':
                        ref_df = sheet
                    elif main_df is None:
                        main_df = sheet
                if main_df is None:
                    # fallback to first sheet
                    main_df = list(sheets.values())[0]
                df_uploaded = main_df
            
            # Process
            df_processed = process_masterlist(df_uploaded, st.session_state.start_date, client_select)

            # Calculate account counts per agent (TOTAL_WOA, POSITIVE, RPC, NEGATIVE)
            try:
                account_counts = count_accounts_per_agent(df_uploaded)
                if not account_counts.empty:
                    # Drop the zero placeholder columns from df_processed first
                    for col in ['TOTAL_WOA', 'POSITIVE', 'RPC', 'NEGATIVE']:
                        if col in df_processed.columns:
                            df_processed = df_processed.drop(columns=[col])
                    
                    # Now merge account counts into processed data by AGENT_USER
                    df_processed = df_processed.merge(account_counts, on='AGENT_USER', how='left')
                    # Fill NaN with 0
                    for col in ['TOTAL_WOA', 'POSITIVE', 'RPC', 'NEGATIVE']:
                        if col in df_processed.columns:
                            df_processed[col] = df_processed[col].fillna(0).astype(int)
                    
                    # Display account summary
                    st.markdown("### 📊 Account Summary by Status")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📞 Total WOA", int(account_counts['TOTAL_WOA'].sum()))
                    with col2:
                        st.metric("✅ Positive", int(account_counts['POSITIVE'].sum()))
                    with col3:
                        st.metric("⚙️ RPC", int(account_counts['RPC'].sum()))
                    with col4:
                        st.metric("❌ Negative", int(account_counts['NEGATIVE'].sum()))
                    st.dataframe(account_counts, use_container_width=True)
                    st.markdown("---")
            except Exception as e:
                st.warning(f"Could not calculate account counts: {str(e)}")

            # Calculate WOA counts per agent by time range
            try:
                woa_per_agent = calculate_woa_per_agent(df_uploaded)
                if not woa_per_agent.empty:
                    # Merge WOA counts into processed data by AGENT_USER
                    df_processed = df_processed.merge(woa_per_agent, on='AGENT_USER', how='left')
                    # Fill NaN with 0 for WOA columns
                    df_processed['TOTAL_WOA (5pm)'] = df_processed['TOTAL_WOA (5pm)'].fillna(0).astype(int)
                    df_processed['TOTAL_WOA (9pm)'] = df_processed['TOTAL_WOA (9pm)'].fillna(0).astype(int)
                    
                    # Display WOA summary
                    st.markdown("### 📈 WOA by Time Range")
                    st.write(f"**12:00 PM - 5:00 PM total: {woa_per_agent['TOTAL_WOA (5pm)'].sum()}**")
                    st.write(f"**5:01 PM - 12:00 AM total: {woa_per_agent['TOTAL_WOA (9pm)'].sum()}**")
                    st.dataframe(woa_per_agent, use_container_width=True)
                    st.markdown("---")
            except Exception as e:
                st.warning(f"Could not calculate WOA: {str(e)}")

            # Calculate PTP and Payment records per agent
                         # Calculate PTP and Payment records per agent
            try:
                ptp_payment_data = get_ptp_and_payment_data(df_uploaded)

                if not ptp_payment_data.empty:
                    ptp_payment_data['PARTIAL_AMOUNT'] = (
                        ptp_payment_data['PTP_PARTIAL_AMOUNT'].fillna(0) +
                        ptp_payment_data['PAYMENT_PARTIAL_AMOUNT'].fillna(0)
                    )

                    ptp_payment_data['PARTIAL_COUNT'] = (
                        ptp_payment_data['PTP_PARTIAL_COUNT'].fillna(0).astype(int) +
                        ptp_payment_data['PAYMENT_PARTIAL_COUNT'].fillna(0).astype(int)
                    )

                    ptp_payment_data['SETTLEMENT_AMOUNT'] = (
                        ptp_payment_data['PTP_SETTLEMENT_AMOUNT'].fillna(0) +
                        ptp_payment_data['PAYMENT_SETTLEMENT_AMOUNT'].fillna(0)
                    )

                    ptp_payment_data['SETTLEMENT_COUNT'] = (
                        ptp_payment_data['PTP_SETTLEMENT_COUNT'].fillna(0).astype(int) +
                        ptp_payment_data['PAYMENT_SETTLEMENT_COUNT'].fillna(0).astype(int)
                    )

                    st.markdown("### 💰 PTP & Payment — Partial vs Settlement")

                    a1, a2 = st.columns(2)
                    a1.metric(
                        "Partial Amount (PTP+Payment)",
                        f"AED {ptp_payment_data['PARTIAL_AMOUNT'].sum():,.2f}"
                    )
                    a2.metric(
                        "Settlement Amount (PTP+Payment)",
                        f"AED {ptp_payment_data['SETTLEMENT_AMOUNT'].sum():,.2f}"
                    )

                    b1, b2 = st.columns(2)
                    b1.metric(
                        "Partial Count (PTP+Payment)",
                        int(ptp_payment_data['PARTIAL_COUNT'].sum())
                    )
                    b2.metric(
                        "Settlement Count (PTP+Payment)",
                        int(ptp_payment_data['SETTLEMENT_COUNT'].sum())
                    )

                    st.dataframe(
                        ptp_payment_data[
                            [
                                'AGENT_USER', 'AGENT_NAME',
                                'PARTIAL_COUNT', 'PARTIAL_AMOUNT',
                                'SETTLEMENT_COUNT', 'SETTLEMENT_AMOUNT'
                            ]
                        ],
                        width=1000
                    )
                else:
                    st.warning("No PTP/Payment data found.")

            except Exception as e:
                st.warning(f"Could not calculate PTP/Payment: {str(e)}")
            
            # Store in session state for the add button
            st.session_state.pending_upload = {
                "df_processed": df_processed,
                "client_select": client_select
            }
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
        
        # Add button to confirm
        if st.button("✅ Add Data to Grid", use_container_width=True, key="add_data_btn"):
            try:
                df_processed = st.session_state.pending_upload['df_processed']
                client_select = st.session_state.pending_upload['client_select']
                
                # Get current session data
                current_session_data = st.session_state.enbd_data if client_select == "ENBD" else st.session_state.eib_data
                
                # Ensure AGENT_USER exists in processed
                if "AGENT_USER" not in df_processed.columns:
                    df_processed["AGENT_USER"] = df_processed["AGENT_NAME"].map({v: k for k, v in AGENT_USER_TO_NAME.items()}).fillna("")

                # Merge uploaded data with current session data by AGENT_USER (accumulate/update)
                if not current_session_data.empty:
                    # Create a copy of current data
                    merged = current_session_data.copy()
                    
                    # For each uploaded agent, update or add their metrics
                    for idx, row in df_processed.iterrows():
                        agent_user = row['AGENT_USER'] if 'AGENT_USER' in row.index else ''
                        
                        # Find row in merged by AGENT_USER
                        matching_rows = merged[merged['AGENT_USER'] == agent_user]
                        
                        if not matching_rows.empty:
                            # Update existing agent's metrics
                            match_idx = matching_rows.index[0]
                            for col in ['TOTAL_WOA (5pm)', 'TOTAL_WOA (9pm)', 'TOTAL_WOA', 'POSITIVE', 'RPC', 'NEGATIVE', 'PTP_PAYMENT_COUNT', 'PTP_PAYMENT_AMOUNT', 'PTP_PARTIAL_COUNT', 'PTP_PARTIAL_AMOUNT', 'PAYMENT_PARTIAL_COUNT', 'PAYMENT_PARTIAL_AMOUNT', 'PTP_SETTLEMENT_COUNT', 'PTP_SETTLEMENT_AMOUNT', 'PAYMENT_SETTLEMENT_COUNT', 'PAYMENT_SETTLEMENT_AMOUNT']:
                                if col in row.index and pd.notna(row[col]):
                                    merged.at[match_idx, col] = row[col]
                        else:
                            # Add new agent (shouldn't happen as defaults include all agents)
                            merged = pd.concat([merged, pd.DataFrame([row])], ignore_index=True)
                    
                else:
                    # No existing data, use defaults and overlay processed values
                    merged = get_default_data_for_client(client_select, st.session_state.start_date)
                    
                    for idx, row in df_processed.iterrows():
                        agent_user = row['AGENT_USER'] if 'AGENT_USER' in row.index else ''
                        matching_rows = merged[merged['AGENT_USER'] == agent_user]
                        
                        if not matching_rows.empty:
                            match_idx = matching_rows.index[0]
                            for col in ['TOTAL_WOA (5pm)', 'TOTAL_WOA (9pm)', 'TOTAL_WOA', 'POSITIVE', 'RPC', 'NEGATIVE', 'PTP_PAYMENT_COUNT', 'PTP_PAYMENT_AMOUNT', 'PTP_PARTIAL_COUNT', 'PTP_PARTIAL_AMOUNT', 'PAYMENT_PARTIAL_COUNT', 'PAYMENT_PARTIAL_AMOUNT', 'PTP_SETTLEMENT_COUNT', 'PTP_SETTLEMENT_AMOUNT', 'PAYMENT_SETTLEMENT_COUNT', 'PAYMENT_SETTLEMENT_AMOUNT']:
                                if col in row.index and pd.notna(row[col]):
                                    merged.at[match_idx, col] = row[col]

                # Store updated data
                if client_select == "ENBD":
                    st.session_state.enbd_data = merged
                else:
                    st.session_state.eib_data = merged
                
                # Clear pending upload
                st.session_state.pending_upload = None
                
                st.success(f"✓ Data added to {client_select} grid!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error adding data: {str(e)}")



# ────────────────────────────────────────────────────────────────────────────────────

def display_payment_data_overview():
    """Display payment data processing overview"""
    st.subheader("💰 Payment Data Processing Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📥 Input Payment Data
        - **Daily Upload File**: Payment transactions
        - **Data Points**: 
          - Agent ID
          - Payment Type (Partial/SPP)
          - AED Amount
          - Customer Reference
          - Date & Time
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Output Metrics
        - **Total Collections**: Sum of all payments
        - **PTP Projection**: Expected payment value
        - **Agent Rankings**: Performance by agent
        - **Payment Breakdown**:
          - Today (Partial/SPP)
          - Yesterday (Partial/SPP)
        """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        **🎯 RPC Payments**
        - Request PTP
        - Confirmation Status
        - Tracking Conversion
        """)
    
    with col2:
        st.success("""
        **✅ Positive Status**
        - Responsive Contacts
        - Active Engagement
        - High Conversion Rate
        """)
    
    with col3:
        st.warning("""
        **⚠️ DPE/PPP/SPP**
        - Down Payment Events
        - Partial Payment Plans
        - Settlement Plans
        """)



# ┌─────────────────────────────────────────────────────────────────────────────────┐
# │                  MAIN APPLICATION LOGIC                       │
# └─────────────────────────────────────────────────────────────────────────────────┘

if not st.session_state.logged_in:
    login_page()
else:
    check_logout()
    
    # Sidebar
    st.sidebar.write(f"👤 **{st.session_state.username}** ({users[st.session_state.username]})")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
    
    st.sidebar.markdown("---")
    
    role = users[st.session_state.username]
    
    # Sidebar tabs
    tabs = ["ENBD", "EIB"]
    if role == "admin":
        tabs.append("DATA")
 
    st.session_state.selected_tab = st.sidebar.radio("📑 Select Tab", tabs)
    
    if st.session_state.selected_tab == "ENBD":
        display_dashboard("ENBD")
    elif st.session_state.selected_tab == "EIB":
        display_dashboard("EIB")
    elif st.session_state.selected_tab == "DATA" and role == "admin":
        admin_data_tab()
   



