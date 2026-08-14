"""Functions for site analytics."""

import base64
from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.figure import Figure

from portal import connect


def plot_users_over_time():
    """Creates a graph of user registrations over time using matplotlib."""
    users = connect.get_user_profiles("root.atlas-af", date_format="object")

    # Naive datetimes on purpose: join_date values from connect.get_user_profiles() are
    # also naive, and this range only feeds a matplotlib x-axis, not a timezone-sensitive comparison.
    datemin = datetime(2021, 7, 1)  # noqa: DTZ001
    datemax = datetime.today()  # noqa: DTZ002

    dates = pd.date_range(datemin, datemax, freq="MS").to_pydatetime().tolist()

    yvalues = []
    for d in dates:
        year = d.year
        month = d.month
        yvalues.append(
            sum(
                u["join_date"].year < year
                or (u["join_date"].year == year and u["join_date"].month <= month)
                for u in users
            )
        )

    # Higher DPI looks much better in HTML
    fig = Figure(figsize=(14, 6), dpi=140, constrained_layout=True)
    ax = fig.subplots()

    ax.plot(dates, yvalues, linewidth=2)

    ax.set_xlabel("Month")
    ax.set_ylabel("Number of users")

    # ----------------------------
    # Nice time axis formatting
    # ----------------------------

    # Major ticks: every 6 months
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # Minor ticks: every month (no labels)
    ax.xaxis.set_minor_locator(mdates.MonthLocator())

    # Label format like "Jan 2024"
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    # Rotate labels so they don't collide
    fig.autofmt_xdate(rotation=30, ha="right")

    # Light grid improves readability in HTML
    ax.grid(True, which="major", axis="y", alpha=0.3)

    # Tighten bounds
    ax.margins(x=0.01)

    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    b64encoding = base64.b64encode(buf.getbuffer()).decode("ascii")
    return b64encoding
