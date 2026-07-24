# Plan de endurecimiento del acceso a datos y robustez del pipeline

> La materia prima del descubrimiento son los datos. El razonamiento científico
> de ACERO ya funciona (astronomía, genómica, cuántica); el cuello de botella
> real es **conseguir los datos reales** y que el pipeline no se rompa. Este plan
> mapea el ecosistema abierto actual (2026), qué es gratis/seguro/verificable, y
> qué es de pago (con precios) para que el humano decida.

## Principios
- Solo datos **públicos, verificables y con procedencia** (URL + sha256). Nunca
  inventados.
- Preferir **repositorios estables con API/REST sin autenticación** para leer.
- Cada fuente entra como **resolvedor**: una referencia (DOI/accesión/consulta) →
  URL(s) de archivo real que la fábrica descarga con su fetch confiable.

## GRATIS + sin llave (implementar ahora)

| Fuente | Qué tiene | Cómo se accede | Estado |
|---|---|---|---|
| **NASA Exoplanet Archive** | planetas, KOI, params estelares | TAP → CSV | ✅ hecho |
| **GEO (NCBI)** | expresión/metilación, matrices | series-matrix + /suppl/ | ✅ hecho |
| **SILSO** | manchas solares | CSV directo | ✅ hecho |
| **Zenodo** | datasets de cualquier campo (QEC, física…) | API `/api/records/{id}` → files | ✅ hecho |
| **Figshare** | datasets generalistas | `/v2/articles/{id}` → download_url | ⏳ implementar |
| **Dryad** | datasets (bio, eco, etc.) | `/api/v2/datasets/{doi}/download` | ⏳ implementar |
| **HEPData** | física de partículas (tablas de papers) | `/record/{id}?format=json` → resources | ⏳ implementar |
| **PubChem** | química (propiedades, bioensayos) | PUG-REST → CSV/JSON, **sin llave** | ⏳ implementar |
| **RCSB PDB** | estructuras de proteínas | archivos estáticos, sin llave | ⏳ nota (más adelante) |
| **UniProt** | proteínas/secuencias | REST → TSV/FASTA, sin llave | ⏳ nota |
| **VizieR/CDS (astronomía)** | miles de catálogos | TAP/ADQL → CSV | ⏳ generalizar |
| **GWOSC (LIGO/Virgo)** | ondas gravitacionales, ruido cuántico | HTTPS directo | ✅ allowlist |
| **AWS Open Data Registry** | 1100+ datasets (genómica, clima, satélite) | S3 público / HTTPS | ⏳ nota (algunos GB) |

### Cruce por coordenadas (resuelve el problema de nombres)
El mayor tropiezo real fue cruzar catálogos por **nombre de estrella** (astronomía)
o por identificador (genómica). Solución del estado del arte, **gratis**:
- **CDS X-Match** (`cdsxmatch.u-strasbg.fr/xmatch`): cruza una tabla local contra
  cualquier tabla VizieR/SIMBAD por posición (RA/Dec, radio), hasta 1e9 filas.
- Regla en el playbook: **cruzar por coordenadas RA/Dec (no por nombre)** cuando
  ambos catálogos las tengan — NASA y VizieR las traen. Esto habría salvado el
  cruce radio×química.

### Librería unificadora (opcional, alto valor)
- **astroquery** (Python, gratis): un solo API para 40+ archivos astronómicos
  (MAST, VizieR, Gaia, SIMBAD, NASA, ALMA, ESO…). Si se agrega a las deps del
  sandbox, la fábrica puede consultarlos sin hardcodear URLs. Nota: requiere red
  en el paso de fetch (no en el sandbox). Evaluar como fase 2.

## GRATIS pero con registro (llave gratuita — nota, decisión humana)
| Fuente | Qué aporta | Costo | Relevancia |
|---|---|---|---|
| **Materials Project** | propiedades de materiales (DFT) | llave gratis | Alta para química/materiales |
| **IBM Quantum** | correr/leer dispositivos cuánticos reales | tier gratis (cola) | Alta para el proyecto cuántico |
| **NASA ADS** | metadatos bibliográficos ricos | token gratis | Media (ya tenemos OpenAlex) |
| **Kaggle Datasets** | miles de datasets curados | llave gratis | Media (calidad variable) |
| **Google Dataset Search** | buscador de datasets | scraping/no API oficial | Media |

## DE PAGO (solo notas con precios — el humano decide)
| Fuente | Qué aporta | Precio aprox. | ¿Vale la pena? |
|---|---|---|---|
| **Web of Science / Scopus** | citas y cobertura bibliográfica premium | institucional, miles USD/año | Bajo: OpenAlex+Crossref cubren gratis casi todo |
| **SciFinder / CAS** | química exhaustiva, reacciones | ~$$$ institucional | Solo si el foco es síntesis química fina |
| **UK Biobank** | fenotipos+genotipos de 500k personas | ~£3-9k por proyecto aprobado | Alto SOLO para un proyecto biomédico serio con IRB |
| **Egress de nube a escala** | mover TBs desde S3/GCS | ~$0.09/GB egress | Evitable: procesar en la nube o bajar subconjuntos |
| **APIs de datos financieros/patentes** | dominios específicos | variable | Solo si el dominio lo exige |

**Recomendación de pago:** por ahora, NADA es necesario. OpenAlex+Crossref
(bibliografía) y los repos abiertos cubren la investigación seria gratis. Las de
registro-gratis (Materials Project, IBM Quantum) sí valen la llave cuando el
proyecto entre a esos dominios. Lo verdaderamente de pago solo se justifica con
un objetivo biomédico/comercial concreto.

## Robustez del pipeline (implementar ahora)
1. **Descarga con reintentos + resume** (HTTP Range): reintenta fallos de red,
   reanuda descargas grandes. (⏳)
2. **Presupuesto de tiempo por descarga** anti-runaway. (✅ hecho, 300s)
3. **Saneo de encoding** (NUL/control, gz). (✅ hecho)
4. **Menú de fuentes en el playbook**: decirle a Codex EXACTAMENTE qué puede
   bajar ACERO, para que no invente URLs inalcanzables. (⏳)
5. **Cruce por coordenadas/ID normalizado** como regla. (⏳ playbook)

## Orden de implementación (esta sesión)
1. Resolvedores gratis sin llave: Figshare, Dryad, HEPData, PubChem.
2. Descarga con reintentos + resume.
3. Menú de fuentes + regla de cruce por coordenadas en el playbook.
4. Notas de pago/registro quedan aquí para tu decisión.
