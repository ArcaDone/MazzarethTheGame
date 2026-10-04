# Consegna PCG — 18 case campione

**Stato al 29 settembre 2026.** La mappa `/Game/Levels/Mazzarino80_CaseStoriche_Campione` è stata salvata con le 18 case generate dal nuovo sistema PCG. È stata riaperta in una sessione pulita dell'editor UE 5.5. La copia PCG di lavoro rimane in `/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext`; la versione precedente del campione è recuperabile da `Saved/Mazzarino80/Backups/Before_PCG_Promotion_2026-09-29/Mazzarino80_CaseStoriche_Campione.umap` (SHA-256 `52D6C035BED363754EF4BCB611B2BC7D83953D62CE8BED5123566293B9B3227F`). Esiste anche la copia iniziale `Saved/Mazzarino80/Backups/Before_PCG_2026-09-29`.

## Sistema consegnato

- `DA_Buildings_Test18` contiene i 18 record `FBuildingData` associati agli ID lotto, con impronte in coordinate mondo, fronte, lati condivisi, famiglia, piani, quote, copertura, facciata, materiali, scelta moduli, rapporto col terreno e seed. Il catalogo tabellare è in `TEST18.md`.
- `BP_ProceduralBuilding` è l'attore di una casa. `PCG_Building_Master` unisce i sottografi `Structure`, `Facades`, `Openings`, `Roofs`, `Details`. Le strutture sono istanziate dal sottografo `Structure`, non soltanto decorate da PCG. I dati di collocazione per lotto sono in `PCGDA_Building_<ID>`; `Scripts/mazzarino80_pcg_refresh_one.py` rigenera un lotto dal suo record e aggiorna mesh, materiali di facciata e copertura, dati PCG e istanze. La classe C++ rende visibili gli attori PCG all'avvio di Play: il volume base di Unreal viene altrimenti caricato come nascosto.
- Le 122 sezioni di superficie importate come Static Mesh comprendono volumi strutturali e facciate/tetti irregolari. La geometria irregolare viene calcolata dal servizio C++ esistente; gli attori precedenti restano nascosti e senza collisione visiva, così le spline manuali degli impianti restano nella mappa. Questo è ancora un passaggio di bake per le forme irregolari: modificare un record richiede la funzione di refresh, non basta cambiare un valore nell'asset e attendere un aggiornamento automatico del grafo.
- Il generatore precedente rimane disponibile per le altre mappe. I Golden Reference approvati e i loro limiti sono in `GOLDEN_STANDARD.md`; le mesh Blender sono state usate come confronto stilistico, mentre i moduli finali si basano soprattutto sulle risorse già importate e sulle finiture del campione.

## Verifiche riuscite

| Controllo | Esito | Evidenza |
|---|---|---|
| Salvataggio e riapertura completa | La nuova `.umap` esiste sul disco ed è stata caricata in una nuova sessione editor; dopo la correzione della visibilità, la mappa è stata salvata e riaperta ancora | `Saved/Mazzarino80/PCG/persist_sample.json`, `open_sample.json` |
| Tutti i lotti | 18 attori PCG generati; 36.987 istanze attese e presenti; 0 mancanti, 0 extra; 0 errori del confronto | `verify_approved_all.json` |
| Impianti e sostituzione | 18 spline/insiemi di spline confrontati con la base; nessuno spostamento rilevato; vecchie superfici nascoste e senza collisione | `verify_context.json` |
| Modifica isolata | Lotto 1249069275: seed 1980→1981, 893→900 punti, altri 17 invariati; ripristino a 893 | `test_isolated_edit.json` |
| Riuso casa 19 | Attore temporaneo con moduli approvati, 893 istanze, poi rimosso; mappa finale a 18 case | `house19_verify.json`, `house19_cleanup.json` |
| Moduli e trasformazioni | 122 mesh importate senza errori; assi e bounding box verificati; confronto fotografico dalla stessa camera | `import_approved_modules.json`, `audit_mesh_bounds.json`, `Golden/Context_Before_01.png`, `Golden/Context_After_01.png` |
| Viste per lotto | 18 viste dall'alto e 18 dalla quota stradale acquisite; per 1249069228 anche 12 punti di vista alternativi | `capture_all_views.json`, `Views/` |
| Play dopo riavvio completo | Il plugin C++ ricompilato mostra da vicino una facciata PCG; 18 attori runtime visibili, 36.987 istanze presenti, 0 errori di confronto | `verify_pie_all.json`, compilazione e prova nell'editor del 29 settembre 2026 |

Le viste principali mostrano le coperture e le facciate delle sei famiglie. Nei vicoli stretti alcune immagini automatiche da quota stradale sono parziali o coperte da edifici vicini: per il lotto 1249069228 la vista alternativa `StreetAlt_1249069228_E1_D700.png` mostra il fronte, mentre `Street_1249069228.png` non è utilizzabile come confronto completo.

## Costo e limiti residui

Il livello usa **264 componenti ISM** per **36.987 istanze**, delle quali **28.283** sono nel passaggio tetti. Le 122 mesh di superficie occupano circa **8,5 MiB** come asset; la mappa finale occupa circa **329 MiB** su disco dopo il salvataggio conclusivo. Questi sono conteggi di geometria e asset, non una misura di FPS o memoria GPU. La facciata è stata osservata da vicino in Play dopo un riavvio completo dell'editor con il plugin C++ aggiornato. `APCGVolume` ripristina la proprietà di attore nascosto quando carica il livello; `AMazzarinoProceduralBuilding::BeginPlay` riattiva la visibilità prima della prova runtime. La stessa classe è usata nella mappa di validazione. Il percorso stradale non è stato percorso integralmente fino a ogni casa durante questa verifica.

Il Map Check manuale del livello finale ha segnalato **0 errori e 198 avvisi**: 180 riguardano le mesh d'erba `SM_FieldGrass_01/02` della scena Comune, prive di collisione benché abilitata, e 18 il raggio nullo del Brush/Volume ereditato dagli attori `BP_ProceduralBuilding`. Gli avvisi sui materiali `M80_Terrazza_calce` e `M80_Coppi_vecchi` relativi a Nanite sono stati risolti salvando i due asset con il flag già attivo. Gli avvisi residui non hanno impedito generazione, persistenza o avvio in Play, ma richiedono attenzione prima di considerare il livello pronto per una build finale.

Il risultato copre **solo** le 18 case del campione. La casa 19 è stata una prova temporanea e non avvia l'espansione del paese.
