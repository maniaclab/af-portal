import base64
from matplotlib.figure import Figure
from io import BytesIO
from datetime import datetime
import pandas as pd
from portal import logger, connect

def plot_users_over_time():
    users = connect.get_group_members("root.atlas-af", date_format=None)
    logger.info(str(users))
    datemin = datetime(2021, 7, 1)
    datemax = datetime.today()
    dates = pd.date_range(datemin, datemax, freq='MS').to_pydatetime().tolist()
    xvalues = list(map(lambda d : d.strftime('%m-%Y'), dates))
    yvalues = [0] * len(xvalues)
    for i in range(len(dates)):
        year = dates[i].year
        month = dates[i].month
        L = list(filter(lambda u : u['join_date'].year < year or (u['join_date'].year == year and u['join_date'].month <= month), users))
        yvalues[i] = len(L)
    fig = Figure(figsize=(16, 8), dpi=80, tight_layout=True)
    ax = fig.subplots()
    ax.plot(xvalues, yvalues)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of users')
    # ax.set_title('Number of users by month')
    buf = BytesIO()
    fig.savefig(buf, format='png')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return data