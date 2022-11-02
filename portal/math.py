''' Functions for site analytics. '''
from portal import connect
from matplotlib.figure import Figure
from datetime import datetime
from io import BytesIO
import base64
import pandas as pd


def plot_users_over_time():
    ''' Creates a graph of user registrations over time using matplotlib. '''
    users = connect.get_user_profiles('root.atlas-af', date_format='object')
    datemin = datetime(2021, 7, 1)
    datemax = datetime.today()
    dates = pd.date_range(datemin, datemax, freq='MS').to_pydatetime().tolist()
    xvalues = list(map(lambda d: d.strftime('%m-%Y'), dates))
    yvalues = [0] * len(xvalues)
    for i in range(len(dates)):
        year = dates[i].year
        month = dates[i].month
        L = list(filter(lambda u: u['join_date'].year < year or (
            u['join_date'].year == year and u['join_date'].month <= month), users))
        yvalues[i] = len(L)
    fig = Figure(figsize=(15, 7), dpi=80, tight_layout=True)
    ax = fig.subplots()
    ax.plot(xvalues, yvalues)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of users')
    buf = BytesIO()
    fig.savefig(buf, format='png')
    b64encoding = base64.b64encode(buf.getbuffer()).decode('ascii')
    return b64encoding
