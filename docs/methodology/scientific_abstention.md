# Scientific Abstention

ACERO must be able to say "I don't know". `inference/engine.py` abstains (and records
why) when: data are insufficient to estimate derivatives reliably; the structure is not
identifiable; several models are observationally equivalent; derivatives cannot be
estimated confidently; extrapolation is unstable; another variable must be measured; or
no affordable experiment distinguishes the candidates. Abstention drops the inference
level to curve_fitting and yields an explicit statement ("no lo sé con los datos
actuales") instead of forcing a winner.
