import streamlit as st
import smartsheet
import pandas as pd
from datetime import datetime

APP_NAME = 'Staff Schedule'

st.set_page_config(page_title=APP_NAME, page_icon='🗓️', layout='centered')

st.image(st.secrets['images']["rr_logo"], width=100)

st.title(APP_NAME)
st.info('See who is working on any given day by department.')


@st.cache_data(ttl=300)
def smartsheet_to_dataframe(sheet_id):
    smartsheet_client = smartsheet.Smartsheet(st.secrets['smartsheet']['access_token'])
    sheet             = smartsheet_client.Sheets.get_sheet(sheet_id)
    columns           = [col.title for col in sheet.columns]
    rows              = []
    for row in sheet.rows: rows.append([cell.value for cell in row.cells])
    return pd.DataFrame(rows, columns=columns)

def parse_date_in_column_headers(col):
    try:
        return pd.to_datetime(col.split()[0], format="%m/%d/%Y").date()
    except Exception:
        return col
    
key  = st.query_params.get('auth')

if "unit" not in st.session_state:
    st.session_state.unit = st.query_params.get('unit', None)

if key != st.secrets['auth']['key']:

    st.warning('Unauthorized access. Please contact your supervisor to obtain access.')

else:

    df              = smartsheet_to_dataframe(st.secrets['smartsheet']['sheets']['schedule'])
    df              = df.set_index(['Department','Employee'])
    df.columns      = [parse_date_in_column_headers(col) for col in df.columns]

    ldf             = smartsheet_to_dataframe(st.secrets['smartsheet']['sheets']['liaisons'])
    ldf             = ldf[~ldf['Unit_Code'].str.startswith('z')]
    ldf             = ldf.iloc[:, :5]
    ldf.columns     = ['Unit_Code', 'HL - Secondary', 'HL - Primary', 'OL - Primary', 'OL - Secondary']

    cdf             = smartsheet_to_dataframe(st.secrets['smartsheet']['sheets']['contacts'])
    cdf             = cdf[['Name', 'Number']]
    cdf.columns     = ['Employee', 'Contact']

    date            = st.date_input('Date', pd.Timestamp.now().date())

    default_unit    = ldf['Unit_Code'].sort_values().unique().tolist().index(st.session_state.unit) if st.session_state.unit in ldf['Unit_Code'].values else None

    if st.session_state.unit != None:

        l, r = st.columns([4, 1],vertical_alignment='bottom')

        l.selectbox('Looking for someone that knows about a specific unit?', options=ldf['Unit_Code'].sort_values().unique(), index=default_unit, key='unit')
        st.query_params["unit"] = st.session_state.unit

        r.button('Clear Unit', on_click=lambda: st.session_state.update(unit=None), width='stretch')
    
    else:
        
        st.selectbox('Looking for someone that knows about a specific unit?', options=ldf['Unit_Code'].sort_values().unique(), index=default_unit, key='unit')
        st.query_params["unit"] = st.session_state.unit

    df              = df[date]
    df              = df.dropna()
    df              = df[~df.str.contains('OFF')]
    df.name         = 'Status'
    df              = df.reset_index()
    df              = df.merge(cdf, on='Employee', how='left').sort_index()

    hod             = df[df['Status'].str.contains('(HOD)', regex=False)]
    assigned_hod    = hod['Employee'].values[0] if not hod.empty else 'None'

    buhod           = df[df['Status'].str.contains('(Backup HOD)', regex=False)]
    assigned_buhod  = buhod['Employee'].values[0] if not buhod.empty else 'None'

    mod             = df[df['Status'].str.contains('(MOD)', regex=False)]
    assigned_mod    = mod['Employee'].values[0] if not mod.empty else 'None'



    with st.container(border=True):

        l, m, r = st.columns(3)

        l.write('**HOD**')
        l.write(assigned_hod)

        m.write('**Backup HOD**')
        m.write(assigned_buhod)

        r.write('**MOD**')
        r.write(assigned_mod)



    if st.session_state.unit != None:

        ldf_filtered    = ldf[ldf['Unit_Code'] == st.session_state.unit]
        employees       = pd.Series(ldf_filtered[['HL - Secondary', 'HL - Primary', 'OL - Primary', 'OL - Secondary']].values.ravel('K')).dropna().unique().tolist()
        df              = df[df.Employee.isin(employees)]

        rank_lookup     = ldf_filtered.drop(columns=['Unit_Code'], inplace=False).melt(var_name='Role', value_name='Who').dropna().set_index('Who')['Role']

        df['Role']      = df['Employee'].map(rank_lookup)
        df.columns      = ['Department', 'Who', 'Status', 'Contact', 'Role']

        df.sort_values(by=['Role'], ascending=True, inplace=True)

    else:

        df.columns = ['Department', 'Who', 'Status', 'Contact']


    for department, df_department in df.groupby('Department'):
            
            with st.expander(f'**{department}**', expanded=(st.session_state.unit != None)):

                df_department = df_department.drop(columns=['Department']).set_index('Who')
                st.dataframe(df_department, width='stretch')