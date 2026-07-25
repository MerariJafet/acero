"""Primer estudio bajo RÉGIMEN DE CONFIRMACIÓN sobre datos reales (Caco-2 / TDC).

Validación de método (recupera una relación conocida, no un 'descubrimiento'):
  descubrir en el split de descubrimiento → congelar protocolo → abrir holdout SELLADO
  → confirmar el MISMO análisis. Todo con la maquinaria real de la CCC.
"""
import tempfile
from pathlib import Path

import numpy as np

from acero.portal.data_resolver import enrich_plan_urls
from acero.portal.experiment_factory import fetch_data
from acero.science.holdout import HoldoutManager, random_split
from acero.science.preregistration import FrozenAnalysisPlan, ProtocolRegistry
from acero.science.search_ledger import SearchSpaceLedger
from acero.science.states import StateEvidence, acero_max_state

# 1) DATOS REALES: Caco-2 (TDC caco2_wang) vía el resolver + descarga confiable
plan = {"data_urls": [{"what": "permeabilidad Caco-2 medida (dataset ADME)"}]}
enr = enrich_plan_urls(plan, domain="chemistry", want_data=True)
d = Path(tempfile.mkdtemp(prefix="confirm_"))
prov = fetch_data(enr["data_urls"], d)
rows = (d / prov[0]["filename"]).read_text().splitlines()[1:]  # salta cabecera
smiles, y = [], []
for r in rows:
    parts = r.split("\t")
    if len(parts) >= 3:
        try:
            y.append(float(parts[2]))
            smiles.append(parts[1])
        except ValueError:
            pass
y = np.array(y)
n = len(y)
print(f"DATOS REALES: {n} moléculas de Caco-2 (TDC), fuente {prov[0]['filename']}, "
      f"sha256 {prov[0]['sha256'][:12]}…")

# feature computable desde SMILES: capacidad de puente-H ~ nº de O y N (proxy de TPSA)
polar = np.array([s.upper().count("O") + s.upper().count("N") for s in smiles])


def analyze(idx):
    """El MISMO análisis en cualquier subconjunto: alta vs baja polaridad → permeabilidad."""
    p = polar[idx]
    yy = y[idx]
    med = np.median(p)
    hi = yy[p > med]           # alta polaridad
    lo = yy[p <= med]          # baja polaridad
    diff = float(lo.mean() - hi.mean())      # esperado > 0: menos polar → más permeable
    se = np.sqrt(hi.var(ddof=1) / len(hi) + lo.var(ddof=1) / len(lo))
    t = diff / se if se > 0 else 0.0
    return diff, float(t), bool(abs(t) > 1.96)


# 2) SPLIT determinista: descubrimiento (70%) / holdout SELLADO (30%)
keys = [str(i) for i in range(n)]
split = random_split(keys, holdout_frac=0.30, salt="caco2-2026")
reg = ProtocolRegistry()
mgr = HoldoutManager(split, reg)
disc_idx = np.array(sorted(int(k) for k in mgr.discovery_keys()))
print(f"\nSplit: descubrimiento={len(disc_idx)}  holdout(sellado)={len(split.holdout_keys)}")

# 3) RÉGIMEN A — DESCUBRIMIENTO (libre) sobre el split de descubrimiento
ledger = SearchSpaceLedger(mission_id="caco2")
ledger.dataset("tdc:caco2_wang")
ledger.hypothesis("polaridad (O+N) vs permeabilidad Caco-2")
ledger.mark_data_seen()
ledger.model("t de dos muestras por mediana de polaridad")
d_diff, d_t, d_det = analyze(disc_idx)
print(f"\n[DESCUBRIMIENTO] efecto (baja−alta polaridad) = {d_diff:.3f} logPapp, "
      f"t = {d_t:.2f}, detectado = {d_det}")
reg_before = reg.classify(None)
print(f"régimen antes de congelar: {reg_before.value} (exploratorio por construcción)")

# 4) CONGELAR PROTOCOLO (antes de tocar el holdout)
protocol = FrozenAnalysisPlan(
    hypothesis="las moléculas de MAYOR polaridad (O+N) tienen MENOR permeabilidad Caco-2",
    primary_variable="logPapp (Y)", population="fármacos del dataset TDC caco2_wang",
    inclusion_criteria="SMILES válido y Y numérico",
    exclusion_criteria="filas sin SMILES o sin Y",
    variable_transform="conteo O+N; corte por la mediana de polaridad",
    statistical_model="comparación de dos grupos (alta vs baja polaridad)",
    primary_test="t de dos muestras", multiplicity_correction="ninguna (1 prueba primaria)",
    min_effect_size=0.20, decision_rule="|t|>1.96 y efecto en la dirección predicha (>0)",
    failure_conditions="efecto <=0 o |t|<=1.96 en el holdout")
pre = reg.freeze(protocol)
print(f"\n[PROTOCOLO CONGELADO] hash = {pre.hash[:22]}…")

# 5) ABRIR EL HOLDOUT (solo posible tras congelar) — RÉGIMEN B
hold_keys = mgr.reveal_holdout(pre.hash)          # gated: exige protocolo congelado
hold_idx = np.array(sorted(int(k) for k in hold_keys))
h_diff, h_t, h_det = analyze(hold_idx)
regime_after = reg.classify(pre.hash)
print(f"[HOLDOUT ABIERTO] unblinding registrado; régimen = {regime_after.value}")
print(f"[CONFIRMACIÓN] efecto = {h_diff:.3f} logPapp, t = {h_t:.2f}, detectado = {h_det}")

# 6) VEREDICTO según la regla de decisión CONGELADA (no post-hoc)
confirmed = h_det and h_diff > 0
print(f"\n=== VEREDICTO (regla congelada) ===")
print(f"predicción: mayor polaridad → menor permeabilidad (efecto > 0)")
print(f"confirmado en holdout: {'SÍ' if confirmed else 'NO'}")

# 7) ESTADO CIENTÍFICO ALCANZADO (máquina de estados de la CCC)
ev = StateEvidence(hypothesis_formulated=True, executed_with_null_test=True,
                   robust=d_det, protocol_frozen=True, holdout_confirmed=confirmed)
state = acero_max_state(ev)
print(f"\nestado ACERO alcanzado: {state.name}")
print(f"deuda de exploración: {ledger.debt_level()} "
      f"(comparaciones efectivas={ledger.effective_comparisons()})")
print("nota: es VALIDACIÓN DE MÉTODO (relación TPSA↔permeabilidad ya conocida), "
      "no un descubrimiento; el techo sigue siendo revisión humana.")
