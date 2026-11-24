import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parent
DATE = "2026-11-23"
PREV = "2026-11-20"
NEXT = "2026-11-24"
# Human-reviewed chart labels, not an automated OCR extraction.
# id: (previous, current, source chart number, unit)
READINGS = {
    "spx.close": (6910.39, 7237.17, 1, "points"),
    "spx.low": (6882.66, 7152.66, 1, "points"),
    "spx.high": (7198.67, 7295.60, 1, "points"),
    "spx.ema5": (None, 7207.23, 1, "points"),
    "spx.ema20": (None, 7426.71, 1, "points"),
    "spx.ema50": (None, 7548.06, 1, "points"),
    "spx.ema200": (None, 7358.81, 1, "points"),
    "pmo.daily": (-1.47, -1.53, 1, "oscillator"),
    "pmo.daily_signal": (-0.79, -0.92, 1, "oscillator"),
    "pmo.weekly": (2.07, 1.79, 2, "oscillator"),
    "pmo.monthly": (12.87, 13.11, 3, "oscillator"),
    "sto.breadth": (-384.39, -336.09, 4, "oscillator"),
    "sto.volume": (-481.60, -399.66, 4, "oscillator"),
    "itbm": (-11.34, -23.93, 5, "oscillator"),
    "itvm": (-107.76, -118.58, 5, "oscillator"),
    "breadth.above20": (21.8, 38.4, 6, "percent"),
    "breadth.above50": (36.2, 48.0, 6, "percent"),
    "breadth.above200": (47.4, 55.4, 6, "percent"),
    "breadth.pmo_rising": (6, 26, 7, "percent"),
    "breadth.pmo_buy": (22, 20, 7, "percent"),
    "breadth.pmo_positive": (61, 60, 7, "percent"),
    "breadth.net_advances": (None, 333, 8, "count"),
    "breadth.net_advancing_volume": (None, 3057.40, 8, "chart_units"),
    "breadth.new_highs": (2, 2, 9, "count"),
    "breadth.new_lows": (21, 4, 9, "count"),
    "mcclellan.oscillator": (-94.95, -48.18, 10, "oscillator"),
    "mcclellan.summation": (73.15, 24.99, 10, "oscillator"),
    "sentiment.aaii_bulls": (None, 33.3, 11, "percent"),
    "sentiment.aaii_bears": (None, 42.2, 11, "percent"),
    "sentiment.rydex_ratio": (None, 0.091, 12, "ratio"),
}
def obj(props):
    return {"type":"object","properties":props,"required":list(props),"additionalProperties":False}
def arr(item):
    return {"type":"array","items":item}
def enum(*values):
    return {"enum":list(values)}
string={"type":"string"}
number={"type":"number"}
nullable={"type":["number","null"]}
date={"type":"string","format":"date"}
metric=enum(*READINGS)
common={"schema_version":{"const":"1.0"},"instrument":{"const":"SPX"}}
def schema(name, props):
    return {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":f"urn:decisionpoint:{name}:1",**obj({**common,**props})}
summary_schema=schema("summary",{
    "session_date":date,"comparison_date":date,"source":string,
    "extraction_method":enum("human_reviewed","ocr_reviewed"),
    "readings":arr(obj({"metric":metric,"value":number,"previous":nullable,"change":nullable,
                       "unit":enum("points","oscillator","percent","count","chart_units","ratio"),
                       "chart":{"type":"integer","minimum":1,"maximum":12},"as_of":date,
                       "period_status":enum("final","provisional","lagged")})),
    "regime":string,"interpretation":string,"limitations":arr(string),
    "hypotheses":arr(obj({"id":string,"description":string,"status":enum("supported","weakened","unconfirmed"),"evidence":arr(metric)}))
})
checklist_schema=schema("checklist",{
    "baseline_date":date,"target_session":date,
    "items":arr(obj({"id":string,"metric":metric,"operator":enum("gt","gte","lt","lte"),
                     "threshold":number,"baseline":nullable,"purpose":string,
                     "status":enum("pending","met","not_met","unavailable")})),
    "evaluation_basis":{"const":"session_close"},"notes":arr(string)
})
summary={"schema_version":"1.0","instrument":"SPX","session_date":DATE,"comparison_date":PREV,
         "source":"https://stockcharts.com/freecharts/dpgallery.html","extraction_method":"human_reviewed",
         "readings":[],"regime":"Oversold rebound within damaged trend structure",
         "interpretation":"Broad participation and short-term oscillator recovery support exhaustion; slower momentum and summation remain weak.",
         "limitations":["Friday baselines retained from the prior analysis; absent values remain null.","Weekly and monthly PMO bars are incomplete.","AAII is weekly; exact survey date not printed. Rydex is dated Nov 20.","No automated OCR was implemented."],
         "hypotheses":[
             {"id":"rebound","description":"Oversold relief rally","status":"supported","evidence":["sto.breadth","sto.volume","breadth.pmo_rising","breadth.new_lows","spx.close"]},
             {"id":"continuation","description":"Immediate bearish continuation","status":"weakened","evidence":["spx.close","breadth.net_advances","mcclellan.oscillator"]},
             {"id":"bottom","description":"Durable market bottom","status":"unconfirmed","evidence":["itbm","itvm","mcclellan.summation","breadth.pmo_buy"]}
         ]}
for k,(p,v,c,u) in READINGS.items():
    summary["readings"].append({"metric":k,"value":v,"previous":p,"change":None if p is None else round(v-p,4),
        "unit":u,"chart":c,"as_of":PREV if c==12 else DATE,"period_status":"provisional" if c in (2,3) else "lagged" if c in (11,12) else "final"})
# AAII as_of represents snapshot date, not the unknown exact survey date.
rules=[
("hold_friday_high","spx.close","gte",7198.67,"Hold reclaimed Friday high"),
("reclaim_200ema","spx.close","gte",7358.81,"Reclaim Monday's fixed 200-day EMA reference"),
("sto_b","sto.breadth","gt",-336.09,"Breadth oscillator continues recovering"),
("sto_v","sto.volume","gt",-399.66,"Volume oscillator continues recovering"),
("mcclellan","mcclellan.oscillator","gt",-48.18,"Breadth momentum improves"),
("mcclellan_positive","mcclellan.oscillator","gte",0,"Breadth momentum reaches zero"),
("above20","breadth.above20","gte",50,"Majority above 20 EMA"),
("above50","breadth.above50","gte",50,"Majority above 50 EMA"),
("rising_pmo","breadth.pmo_rising","gte",40,"Momentum participation expands"),
("new_lows","breadth.new_lows","lte",4,"New lows remain subdued"),
("itbm","itbm","gte",-23.93,"Intermediate breadth stabilizes"),
("itvm","itvm","gte",-118.58,"Intermediate volume stabilizes"),
("pmo_buy","breadth.pmo_buy","gt",20,"PMO buy signals expand"),
("summation","mcclellan.summation","gte",24.99,"Summation stabilizes"),
("protect_friday_low","spx.close","gt",6882.66,"Avoid closing below Friday low")
]
checklist={"schema_version":"1.0","instrument":"SPX","baseline_date":DATE,"target_session":NEXT,
           "evaluation_basis":"session_close","notes":["Thresholds are monitoring hypotheses, not backtested trading signals.","Compare fixed baseline levels, not moving intraday thresholds.","Intraday rejection or acceptance requires separate price action analysis."],
           "items":[{"id":i,"metric":m,"operator":o,"threshold":t,"baseline":READINGS[m][1],"purpose":p,"status":"pending"} for i,m,o,t,p in rules]}
for name,sch,doc in [("summary",summary_schema,summary),("checklist",checklist_schema,checklist)]:
    Draft202012Validator.check_schema(sch)
    Draft202012Validator(sch,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(doc)
    for filename,data in [(f"{name}.schema.json",sch),(f"{name}-{DATE}.json",doc)]:
        (ROOT/filename).write_text(json.dumps(data,indent=2)+"\n")
    print(f"{name}: validated")
