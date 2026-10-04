# Kit Blender → PCG: stato della prova

> **Direzione aggiornata, 2 ottobre 2026:** il kit di case complete è sospeso.
> Nessuna parete o casa del kit va promossa nella mappa
> `Mazzarino80_CaseStoriche_Campione`. Il lavoro attivo riguarda i materiali
> delle case PCG approvate e solo dettagli singoli compatibili. Vedi
> `APPROVED_PCG_DETAIL_MATERIAL_STATUS.md` per la prova corrente.

## Pronto per la verifica

- La scena Blender 4.3 contiene i quattro piloti e il kit riutilizzabile. Sono stati esportati 53 moduli indipendenti, quattro assemblaggi di riferimento e 17 mesh di stadio per il controllo. I pivot dei moduli sono stati corretti e misurati in Unreal.
- In Unreal i 74 asset importati (moduli, piloti e stadi) usano un master PBR condiviso con otto istanze di superficie. I due camini che avevano uno slot grigio provvisorio usano ora la finitura di intonaco usurato.
- `L_ReuseKit_QA` contiene i quattro assemblaggi statici accanto al manichino; `L_ReuseKit_PCG_QA` contiene quattro volumi PCG e grafi separati in Structure, Facades, Openings, Roofs e Details.
- Ogni lotto del catalogo principale e ogni punto PCG dei 18 lotti porta ora `VisualStyle`, indipendente dalla famiglia geometrica.
- La variante PCG in `ReuseKit/PCG/Lots` conserva tutti i punti originali e i 18 tetti diversi. Sostituisce solo 20 ringhiere provvisorie con la mesh alleggerita del kit, adattata al precedente ingombro. La mappa approvata e i suoi grafi di lotto restano invariati.
- `L_ReuseKit_4Lots_QA` è una copia della mappa di validazione dei lotti irregolari: i quattro piloti usano i grafi candidati; gli altri 14 mantengono i grafi preesistenti. L'audit conferma i 18 volumi dei lotti e nessun lotto perso.
- `L_ReuseKit_18Lots_QA` contiene la variante candidata su tutti i 18 lotti, senza modificare la mappa approvata. Il diciannovesimo volume presente nella copia è il cubo di prova `M80_PCG_Validation_Cube` già esistente nella mappa sorgente.
- Le due mappe dei lotti includono un manichino di riferimento per ciascuno dei quattro piloti, collocato fuori dalle impronte degli edifici vicino all'ingresso.

## Ancora da verificare prima della distribuzione

- I quattro grafi PCG della mappa QA sono stati salvati, ma il commandlet senza renderer ha annullato la generazione pianificata alla chiusura: l'audit vede quattro volumi e **zero istanze persistenti**. Aprire la mappa nell'editor grafico, generare e verificare da strada/cortile/tetto prima di promuovere il risultato.
- Il test dei 18 lotti è una **variante candidata**. Richiede confronto visivo in Unreal, controllo delle ringhiere nei balconi reali e misura delle prestazioni prima di rimpiazzare i grafi della mappa principale.
- Il tentativo automatico di cattura grafica con D3D11 è stato interrotto durante una lunga compilazione iniziale degli shader, prima del caricamento della mappa. Non c'è ancora uno screenshot Unreal verificato né un dato FPS affidabile.
- Le mesh di tetto dei piloti servono al confronto, non alla distribuzione. Conservare le coperture irregolari per lotto e aggiungere varianti solo con attacchi affidabili. Non replicare i quattro edifici completi sugli altri lotti.
- Aperture, angoli, muri e dettagli del kit richiedono regole di incastro e controllo UV/tangenti sui singoli asset prima di sostituire le superfici C++ dei 18 lotti.

## Rapporti automatici

- `reuse_import_result.json`, `reuse_master_material_result.json`, `module_pivot_probe.json`
- `reuse_qa_audit.json`, `reuse_pcg_qa_audit.json`
- `reuse_lot_candidate_report.json`, `reuse_lot_candidate_audit.json`
- `reuse_lots_pilot_map.json`, `reuse_lots_pilot_map_audit.json`
- `reuse_lots_all_map.json`, `reuse_lots_all_map_audit.json`
- `reuse_scale_mannequins.json`
