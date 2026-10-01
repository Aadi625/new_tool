from flask import Flask, jsonify, request, render_template

app = Flask(__name__)


# ============================================================
# ASSET CLASSES
# ============================================================

ASSETS = [
    "Large Cap Equity",
    "Mid & Small Cap Equity",
    "Debt Funds / Bonds",
    "Gold",
    "International Equity",
    "Real Estate / REITs",
    "AIF / PMS (Illiquid)",
    "Cash",
]

DEFAULTS = [6.0, 3.0, 5.0, 1.5, 2.0, 2.0, 1.5, 1.0]

LIQUID = [
    "Large Cap Equity",
    "Mid & Small Cap Equity",
    "Debt Funds / Bonds",
    "Gold",
    "International Equity",
    "Cash",
]

PLEDGEABLE = [
    "Large Cap Equity",
    "Mid & Small Cap Equity",
]


# ============================================================
# HISTORICAL SCENARIOS
# Approximate peak-to-trough movements in INR terms
# ============================================================

HISTORICAL = {

    "Global Financial Crisis (2008)": {
        "Large Cap Equity": -0.55,
        "Mid & Small Cap Equity": -0.70,
        "Debt Funds / Bonds": 0.05,
        "Gold": 0.25,
        "International Equity": -0.40,
        "Real Estate / REITs": -0.30,
        "AIF / PMS (Illiquid)": -0.50,
        "Cash": 0.0,
    },

    "COVID crash (Feb-Mar 2020)": {
        "Large Cap Equity": -0.38,
        "Mid & Small Cap Equity": -0.42,
        "Debt Funds / Bonds": 0.00,
        "Gold": 0.05,
        "International Equity": -0.28,
        "Real Estate / REITs": -0.10,
        "AIF / PMS (Illiquid)": -0.35,
        "Cash": 0.0,
    },

    "Taper tantrum (2013)": {
        "Large Cap Equity": -0.15,
        "Mid & Small Cap Equity": -0.20,
        "Debt Funds / Bonds": -0.05,
        "Gold": 0.10,
        "International Equity": 0.10,
        "Real Estate / REITs": -0.05,
        "AIF / PMS (Illiquid)": -0.15,
        "Cash": 0.0,
    },

    "Demonetisation (2016)": {
        "Large Cap Equity": -0.10,
        "Mid & Small Cap Equity": -0.15,
        "Debt Funds / Bonds": 0.02,
        "Gold": -0.05,
        "International Equity": 0.02,
        "Real Estate / REITs": -0.15,
        "AIF / PMS (Illiquid)": -0.10,
        "Cash": 0.0,
    },

    "Global rate hikes (2022)": {
        "Large Cap Equity": -0.15,
        "Mid & Small Cap Equity": -0.20,
        "Debt Funds / Bonds": -0.02,
        "Gold": 0.05,
        "International Equity": -0.15,
        "Real Estate / REITs": -0.05,
        "AIF / PMS (Illiquid)": -0.15,
        "Cash": 0.0,
    },
}


# ============================================================
# CUSTOM SHOCK SLIDERS
# ============================================================

SLIDERS = [

    {
        "id": "lc",
        "label": "Large cap equity change (%)",
        "min": -70,
        "max": 30,
        "default": -30,
    },

    {
        "id": "mc",
        "label": "Mid & small cap equity change (%)",
        "min": -80,
        "max": 30,
        "default": -40,
    },

    {
        "id": "rate_bps",
        "label": "Interest rate change (bps)",
        "min": -300,
        "max": 500,
        "default": 200,
    },

    {
        "id": "gold",
        "label": "Gold change (%)",
        "min": -40,
        "max": 60,
        "default": 10,
    },

    {
        "id": "global_eq",
        "label": "Global equities change in USD (%)",
        "min": -60,
        "max": 30,
        "default": -20,
    },

    {
        "id": "inr",
        "label": "Rupee depreciation vs USD (%)",
        "min": -20,
        "max": 40,
        "default": 10,
    },

    {
        "id": "real_estate",
        "label": "Real estate change (%)",
        "min": -50,
        "max": 20,
        "default": -15,
    },

    {
        "id": "aif",
        "label": "AIF / PMS change (%)",
        "min": -60,
        "max": 20,
        "default": -25,
    },
]


# ============================================================
# HELPERS
# ============================================================

def num(value, default, low, high):
    """Convert user input into a safe number within limits."""

    try:
        x = float(value)
    except (TypeError, ValueError):
        return default

    return max(low, min(high, x))


def crore(x):
    """Format a number as ₹ crore."""

    sign = "-" if x < 0 else ""

    return f"{sign}₹{abs(x):,.2f} Cr"


# ============================================================
# PORTFOLIO ANALYSIS ENGINE
# ============================================================

def analyse(holdings, shocks, loan, max_ltv):

    rows = []

    before = 0.0
    after = 0.0
    liquid = 0.0
    pledged = 0.0

    for asset in ASSETS:

        value = holdings[asset]

        shock = shocks.get(asset, 0.0)

        pnl = value * shock

        after_value = value + pnl

        rows.append({
            "asset": asset,
            "before": value,
            "shock": shock * 100,
            "pnl": pnl,
            "after": after_value,
        })

        before += value
        after += after_value

        if asset in LIQUID:
            liquid += after_value

        if asset in PLEDGEABLE:
            pledged += after_value


    # --------------------------------------------------------
    # LEVERAGE CHECK
    # --------------------------------------------------------

    leverage = None

    if loan > 0:

        if pledged <= 0:

            leverage = {
                "status": "bad",
                "text": "No pledged equity left to cover the loan."
            }

        else:

            ltv = loan / pledged * 100

            if ltv > max_ltv:

                shortfall = (
                    loan
                    - (max_ltv / 100) * pledged
                )

                leverage = {
                    "status": "bad",
                    "text":
                        f"Margin call: loan-to-value is "
                        f"{ltv:.1f}%, above the "
                        f"{max_ltv:.0f}% limit. "
                        f"The client must repay or top up "
                        f"about {crore(shortfall)}."
                }

            else:

                leverage = {
                    "status": "ok",
                    "text":
                        f"Loan-to-value after the shock is "
                        f"{ltv:.1f}%, within the "
                        f"{max_ltv:.0f}% limit."
                }


    pnl = after - before

    return {

        "rows": rows,

        "before": before,

        "after": after,

        "pnl": pnl,

        "pct":
            pnl / before * 100
            if before
            else 0,

        "net_worth":
            after - loan,

        "liquid":
            liquid,

        "liquid_pct":
            liquid / after * 100
            if after > 0
            else 0,

        "leverage":
            leverage,
    }


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        inputs=list(zip(ASSETS, DEFAULTS)),
        scenarios=list(HISTORICAL),
        sliders=SLIDERS,
    )


# ============================================================
# STRESS TEST API
# ============================================================

@app.route("/api/stress", methods=["POST"])
def api_stress():

    data = request.get_json(silent=True) or {}

    raw = data.get("holdings") or {}

    holdings = {
        asset: num(
            raw.get(asset),
            0.0,
            0.0,
            1e7
        )
        for asset in ASSETS
    }

    total = sum(holdings.values())

    if total <= 0:

        return jsonify({
            "error":
                "Enter at least one holding to run a stress test."
        })


    # --------------------------------------------------------
    # PORTFOLIO PARAMETERS
    # --------------------------------------------------------

    duration = num(
        data.get("duration"),
        4.0,
        0.0,
        30.0
    )

    convexity = num(
        data.get("convexity"),
        30.0,
        0.0,
        500.0
    )

    loan = num(
        data.get("loan"),
        0.0,
        0.0,
        1e7
    )

    max_ltv = num(
        data.get("max_ltv"),
        50.0,
        10.0,
        80.0
    )


    # --------------------------------------------------------
    # CUSTOM SHOCK
    # --------------------------------------------------------

    custom_raw = data.get("custom") or {}

    custom_values = {

        slider["id"]: num(
            custom_raw.get(slider["id"]),
            slider["default"],
            slider["min"],
            slider["max"]
        )

        for slider in SLIDERS
    }


    # --------------------------------------------------------
    # DEBT IMPACT
    # Duration + convexity approximation
    # --------------------------------------------------------

    dy = (
        custom_values["rate_bps"]
        / 10000
    )

    debt_shock = (
        -duration * dy
        + 0.5
        * convexity
        * dy ** 2
    )


    # --------------------------------------------------------
    # INTERNATIONAL EQUITY
    # USD market move + INR depreciation
    # --------------------------------------------------------

    intl_shock = (

        (1 + custom_values["global_eq"] / 100)

        * (1 + custom_values["inr"] / 100)

        - 1
    )


    custom = {

        "Large Cap Equity":
            custom_values["lc"] / 100,

        "Mid & Small Cap Equity":
            custom_values["mc"] / 100,

        "Debt Funds / Bonds":
            debt_shock,

        "Gold":
            custom_values["gold"] / 100,

        "International Equity":
            intl_shock,

        "Real Estate / REITs":
            custom_values["real_estate"] / 100,

        "AIF / PMS (Illiquid)":
            custom_values["aif"] / 100,

        "Cash":
            0.0,
    }


    # --------------------------------------------------------
    # SELECT HISTORICAL SCENARIO
    # --------------------------------------------------------

    scenario = data.get("scenario")

    if scenario not in HISTORICAL:

        scenario = list(HISTORICAL)[0]


    # --------------------------------------------------------
    # COMPARE ALL SCENARIOS
    # --------------------------------------------------------

    compare = []

    all_scenarios = (
        list(HISTORICAL.items())
        + [("Your custom shock", custom)]
    )

    for name, shocks in all_scenarios:

        result = analyse(
            holdings,
            shocks,
            loan,
            max_ltv
        )

        compare.append({
            "name": name,
            "pnl": result["pnl"],
            "pct": result["pct"],
        })


    historical_only = [
        item
        for item in compare
        if item["name"] in HISTORICAL
    ]

    worst = min(
        historical_only,
        key=lambda item: item["pnl"]
    )

    compare.sort(
        key=lambda item: item["pct"]
    )


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return jsonify({

        "total":
            total,

        "worst": {

            "name":
                worst["name"],

            "after":
                total + worst["pnl"],

            "loss":
                abs(worst["pnl"]),

            "pct":
                abs(worst["pct"]),
        },

        "historical":
            analyse(
                holdings,
                HISTORICAL[scenario],
                loan,
                max_ltv
            ),

        "custom":
            analyse(
                holdings,
                custom,
                loan,
                max_ltv
            ),

        "debt_shock":
            debt_shock * 100,

        "intl_shock":
            intl_shock * 100,

        "compare":
            compare,
    })


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)