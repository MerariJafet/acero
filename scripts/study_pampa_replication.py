"""Réplica en fuente INDEPENDIENTE (PAMPA) del hallazgo Caco-2: polaridad → permeabilidad.
Usa el IndependenceGraph para certificar si cuenta como replicación real."""
import tempfile
from pathlib import Path
import numpy as np
from acero.portal.data_resolver import enrich_plan_urls
from acero.portal.experiment_factory import fetch_data
from acero.science.independence_graph import DatasetProvenance, IndependenceGraph

def load(what, domain="chemistry"):
    enr = enrich_plan_urls({"data_urls":[{"what":what}]}, domain=domain, want_data=True)
    d = Path(tempfile.mkdtemp())
    prov = fetch_data(enr["data_urls"], d)
    rows = (d/prov[0]["filename"]).read_text().splitlines()
    hdr = rows[0]; body = rows[1:]
    sm, y = [], []
    for r in body:
        p = r.split("\t")
        if len(p) >= 3:
            try: y.append(float(p[2])); sm.append(p[1])
            except ValueError: pass
    return prov[0], hdr, sm, np.array(y)

def polarity(sm): return np.array([s.upper().count("O")+s.upper().count("N") for s in sm])

def analyze(sm, y):
    p = polarity(sm); med = np.median(p)
    hi, lo = y[p>med], y[p<=med]
    binary = set(np.unique(y).tolist()) <= {0.0,1.0}
    diff = float(lo.mean()-hi.mean())   # >0 esperado: menos polar → más permeable
    if binary:
        # proporción permeable; test de dos proporciones (z)
        import math
        n1,n0=len(hi),len(lo); p1,p0=hi.mean(),lo.mean()
        pp=(hi.sum()+lo.sum())/(n1+n0); se=math.sqrt(pp*(1-pp)*(1/n1+1/n0))
        z=(p0-p1)/se if se>0 else 0.0
        return {"tipo":"binario (permeable/no)","diff_rate":diff,"stat":z,"detect":abs(z)>1.96,"n":len(y)}
    se=np.sqrt(hi.var(ddof=1)/len(hi)+lo.var(ddof=1)/len(lo)); t=diff/se if se>0 else 0
    return {"tipo":"continuo (logPapp)","diff":diff,"stat":float(t),"detect":abs(t)>1.96,"n":len(y)}

# Caco-2 (original) y PAMPA (independiente)
pc, hc, smc, yc = load("permeabilidad Caco-2 medida (dataset ADME)")
pp, hp, smp, yp = load("permeabilidad PAMPA (dataset pampa_ncats)")
print(f"Caco-2: {pc['filename']} ({len(yc)} mol) | cabecera: {hc}")
print(f"PAMPA : {pp['filename']} ({len(yp)} mol) | cabecera: {hp}\n")
rc = analyze(smc, yc); rp = analyze(smp, yp)
print("Caco-2 :", rc)
print("PAMPA  :", rp)

# ¿misma dirección? (menos polar → más permeable ⇒ diff/diff_rate > 0)
dc = rc.get("diff", rc.get("diff_rate")); dp = rp.get("diff", rp.get("diff_rate"))
same_dir = (dc>0)==(dp>0) and rp["detect"]
print(f"\n¿misma dirección y significativo en PAMPA?: {same_dir}")

# IndependenceGraph: ¿es replicación independiente?
g = IndependenceGraph()
g.add(DatasetProvenance("caco2_wang", assay_source="caco2_wang", instrument="Caco-2 (célula)",
                        cohort="caco2", laboratory="wang", curation_pipeline="TDC", provenance_root="TDC"))
g.add(DatasetProvenance("pampa_ncats", assay_source="pampa_ncats", instrument="PAMPA (membrana artificial)",
                        cohort="ncats", laboratory="ncats", curation_pipeline="TDC", provenance_root="TDC"))
v = g.independence("caco2_wang", "pampa_ncats")
print(f"\nIndependenceGraph: {v.explain()}")
print(f"¿replicación-capaz?: {v.is_replication_capable}")

print("\n=== VEREDICTO ===")
if same_dir and v.is_replication_capable:
    print("REPLICADO_EN_DATASET_INDEPENDIENTE: el efecto polaridad→permeabilidad se sostiene")
    print("en un ensayo distinto (PAMPA vs Caco-2), otra medición, otra cohorte.")
elif same_dir and not v.is_replication_capable:
    print("Dirección coincide PERO comparten raíz de procedencia → NO es replicación plena.")
else:
    print("NO replica: dirección distinta o no significativo.")
print("Nota honesta: ambos vienen del ecosistema TDC (misma raíz de curación) → el grafo")
print("puede degradarlo; una replicación plena exigiría un repositorio de curación distinto.")
