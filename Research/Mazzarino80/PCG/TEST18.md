# Test delle 18 case — stato PCG

Fonte: attori della mappa campione salvata il 29 settembre 2026. I valori edilizi sono quelli della proposta procedurale attuale, non misure storiche certificate. La geometria dei lotti è in coordinate mondo già riflesse su Y.

| ID lotto | Famiglia | Piani principali | Seed | Punti lotto |
|---|---|---:|---:|---:|
| 1249068307 | Piccolo palazzetto | 2 | 4035 | 10 |
| 1249069200 | Casa ampliata | 2 | 3624 | 9 |
| 1249069202 | Casa con piccolo cortile | 2 | 3487 | 13 |
| 1249069204 | Casa d'angolo | 2 | 2802 | 17 |
| 1249069205 | Casa con piccolo cortile | 2 | 3213 | 44 |
| 1249069213 | Casa stretta su più piani | 3 | 2391 | 4 |
| 1249069219 | Casa d'angolo | 2 | 3076 | 7 |
| 1249069228 | Casa con piccolo cortile | 2 | 3350 | 14 |
| 1249069229 | Piccolo palazzetto | 2 | 4309 | 7 |
| 1249069235 | Casa ampliata | 2 | 3761 | 9 |
| 1249069237 | Casa d'angolo | 2 | 2939 | 6 |
| 1249069246 | Piccolo palazzetto | 2 | 4172 | 10 |
| 1249069247 | Casa bassa popolare | 1 | 2254 | 5 |
| 1249069271 | Casa stretta su più piani | 3 | 2528 | 4 |
| 1249069275 | Casa bassa popolare | 1 | 1980 | 7 |
| 1249069276 | Casa stretta su più piani | 3 | 2665 | 8 |
| 1249069286 | Casa bassa popolare | 1 | 2117 | 4 |
| 1249069287 | Casa ampliata | 2 | 3898 | 14 |

## Stato

- Catalogo `DA_Buildings_Test18` acquisito dall'editor, con 18 ID e sei famiglie.
- Il livello consegnato `/Game/Levels/Mazzarino80_CaseStoriche_Campione` contiene 18 attori `BP_ProceduralBuilding` con grafi PCG attivi; la vecchia geometria resta nascosta come servizio per i perimetri irregolari e conserva le spline degli impianti.
- Dopo riavvio completo dell'editor: 36.987 istanze attese e 36.987 presenti, nessuna mancante o aggiuntiva, nessun componente PCG partizionato. Riferimenti: `Saved/Mazzarino80/PCG/verify_approved_all.json` e `verify_context.json`.
- 36 viste dall'alto e dalla quota stradale sono in `Saved/Mazzarino80/PCG/Views`; la vista stradale automatica del lotto 1249069228 è occultata dal vicino, perciò sono state acquisite anche viste alternative dello stesso lotto.
- La prova isolata del lotto 1249069275 ha cambiato il seed 1980→1981 (893→900 punti), lasciato invariati gli altri 17 lotti, quindi ripristinato i 893 punti iniziali. La casa 19 temporanea ha generato 893 istanze con moduli esistenti ed è stata rimossa dalla mappa.

## Vincoli di validazione

Conservare i 18 ID, le impronte XY, le case verticali su Z, le strade, il terreno, le strutture personali e i percorsi manuali degli impianti. Confrontare volume, silhouette, aperture e materiali con le stesse camere prima di sostituire il campione.

I risultati, le verifiche Play e i limiti residui sono descritti in `RAPPORTO_CONSEGNA_18_CASE_2026-09-29.md`.
