# Aggiornamento finiture PCG delle 18 case — 30 settembre 2026

La mappa campione `/Game/Levels/Mazzarino80_CaseStoriche_Campione` contiene la versione PCG aggiornata delle 18 case. Il materiale grigio uniforme delle facciate è stato sostituito con una palette di muratura locale, calce consumata, intonaco ocra e laterizio. Il materiale di cemento dipinto che produceva una dominante blu-grigia in ombra è stato tolto dai master delle case campione. Le fughe, il rilievo normale e la rugosità dei mattoni sono stati ridotti dopo un confronto con e senza mappa normale dalla stessa camera: la parte del chiaroscuro che restava sulla parete chiara dipendeva invece dalla finitura e dall'illuminazione, non da una normale invertita.

Le finiture usano le texture già importate da Comune e le mappe `T_Bricks`/`T_Wall` importate nel progetto. Il rumore macro in coordinate mondo limita la ripetizione su grandi facciate; le tonalità sono salvate nelle singole istanze dei lotti, quindi restano modificabili senza cambiare la geometria. La pietra di soglie e gradini ha una tinta più calda e rugosità opaca. Le false placche bianche di rottura sono state rimosse; le aperture murate sono rese con tavole. I due muri dei cortili sono stati suddivisi in blocchi a scala plausibile anziché stirare una singola texture su diversi metri.

## Verifiche dopo il salvataggio

| Controllo | Risultato | Traccia |
|---|---|---|
| Mappa campione riaperta | 18 attori PCG, 37.109 istanze, 1.034 attori con spline nel livello | `Saved/Mazzarino80/PCG/verify_promoted_sample.json` |
| Materiali e proporzioni | 18 case, 41 materiali distinti, 0 materiali mancanti e 0 avvisi automatici di scala | `Saved/Mazzarino80/PCG/audit_material_scale18.json` |
| Generazione | 37.109 istanze attese e presenti, 28.259 coppi, 0 lotti mancanti o discordanti | `Saved/Mazzarino80/PCG/verify_18_validation.json` |
| Play | 18 case visibili, 37.109 istanze, 0 errori e 0 extra | `Saved/Mazzarino80/PCG/verify_pie_weathered.json` |
| Viste finali | 18 dall'alto e 18 da strada, acquisite dopo le modifiche ai materiali | `Saved/Mazzarino80/PCG/CharacterViewsAll/`, `capture_character_all_views.json` |

La precedente mappa campione è recuperabile sia come asset `/Game/Mazzarino80/PCG/Backups/L_CaseStoriche_BeforeWeatheredFinish_20260930` sia come file in `Saved/Mazzarino80/Backups/Before_weathered_finish_2026-09-30/Mazzarino80_CaseStoriche_Campione.umap` (SHA-256 `1A45427029FE531DC6D40A1FBFD3EE9F07FA45B799B512A0AE7893C1AC1A2DC7`). La mappa PCG di lavoro rimane in `/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext`.

## Limiti visivi e prestazionali

L'audit automatico dimostra che i materiali sono assegnati e che le dimensioni delle mesh rientrano nei controlli impostati; non equivale all'approvazione artistica di ogni parete. Alcune viste automatiche da strada sono coperte dagli edifici vicini. Le superfici stradali e alcuni pavimenti di cortile del contesto appaiono ancora lisci e riflettenti: sono esterni alle finiture delle facciate PCG e richiedono una passata dedicata. Alcune soglie, finestre e scale risultano ancora troppo chiare al sole; i tetti e le murature ripetono moduli a distanza ravvicinata. Le istanze sono raggruppate in 260 componenti ISM, ma non è stata misurata una frequenza FPS rappresentativa né l'uso di memoria GPU: il passaggio all'intero paese va preceduto da un profilo prestazionale in una build rappresentativa.

Per i perimetri irregolari resta il passaggio di bake dal servizio C++ preesistente descritto nel rapporto del 29 settembre; la modifica di un record richiede il refresh del lotto. La prova temporanea della casa 19 è documentata nel rapporto precedente e la mappa consegnata resta a 18 case.
