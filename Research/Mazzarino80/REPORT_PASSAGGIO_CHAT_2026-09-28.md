# Mazzarino anni Ottanta — report per continuare in una nuova chat

**Aggiornato al 28 settembre 2026, dopo la rifinitura delle 18 case.**

Questo documento riassume il lavoro completato, le decisioni dell'utente, lo stato verificato e le attività ancora necessarie. Non è una certificazione di ricostruzione storica o di qualità finale. Leggerlo prima di modificare la scena.

## 1. Obiettivo e decisioni dell'utente

Ricreare Mazzarino nei primi anni Ottanta come paese siciliano abitato, composto soprattutto da case storiche precedenti alla seconda guerra mondiale, modificate e mantenute in modo disomogeneo nei decenni successivi.

Il carattere desiderato è popolare, mediterraneo e arabo-siciliano: case addossate, vicoli raccolti, murature spesse, volumi irregolari, profondità dei prospetti, coppi, balconi, terrazze, superfici consumate. L'impronta araba riguarda il tessuto urbano; non introdurre automaticamente cupole, minareti o archi decorativi ovunque. L'età degli edifici non implica un paese abbandonato o distrutto dalla guerra.

Decisioni già prese:

- Conservare tracciati reali, perimetri, punti riconoscibili e quote documentate; distinguere questi dati dalle proposte architettoniche.
- Riutilizzare gli edifici e le risorse già presenti nel progetto **Comune**.
- Rendere strade e impianti modificabili attraverso spline.
- **Rifinire prima le 18 case campione. Non distribuire ancora il nuovo generatore su tutto il paese.**
- Rimuovere dalla mappa campione la generazione precedente e mantenere soltanto le nuove 18 case, oltre a terreno, strade e strutture personali.
- Case sempre verticali rispetto allo **Z globale**, con solai orizzontali: cambiando terreno o quota delle spline devono aggiornare appoggi e fondazioni senza inclinarsi.
- Esporre dimensioni, materiali, visibilità, famiglia e seed; consentire la rigenerazione di una sola casa.

Le immagini dell'utente guidano la qualità: case modeste e usura differenziata sono il riferimento principale; edifici monumentali e balconi molto ricchi sono eccezioni. Google Maps moderno serve a leggere proporzioni e composizione, non a dimostrare l'aspetto del 1980.

## 2. Progetto e mappa da usare

| Elemento | Percorso / stato |
|---|---|
| Progetto attivo | `D:\UE5Projects\GameAnimationSample\MazzarethTheGame.uproject` |
| Versione usata | Unreal Engine 5.5.3, installazione `D:\UE_5.5` |
| **Mappa attuale** | `/Game/Levels/Mazzarino80_CaseStoriche_Campione` |
| File della mappa | `D:\UE5Projects\GameAnimationSample\Content\Levels\Mazzarino80_CaseStoriche_Campione.umap` |
| Cartella Outliner | `Mazzarino80/Campione_case_storiche`, suddivisa per famiglia |
| Panoramica precedente | `/Game/Levels/Mazzarino80_Panoramica`, conservata |
| Mappa originale | `/Game/Levels/MazzarethMap`, conservata |
| Catalogo strutture personali | `/Game/Levels/Mazzarino80_Catalogo` |
| Progetto sorgente delle risorse | `D:\UE5Projects\Comune`, letto senza modificarlo |

L'EditorStartupMap punta al campione; il GameDefaultMap rimane `/Game/Levels/Main`. Aprire la mappa corretta prima di avviare una prova con il personaggio.

All'ultimo controllo la mappa era aperta dalla camera del vicolo, il salvataggio era riuscito e non rimanevano pacchetti sporchi. La nuova chat deve controllare lo stato corrente: l'utente potrebbe aver modificato la scena nel frattempo.

**Attenzione ai documenti più vecchi:** `STATO_2026-09-28.md` descrive principalmente la fase delle strade; `LEGGIMI_Edifici.md` descrive anche il generatore precedente. Per le case attuali usare questo report e la sezione finale di `LEGGIMI_CaseStoriche.md`.

## 3. Lavoro precedente: terreno, orientamento, strade e strutture

La base iniziale era `Mazzarino80_Base`, copia di MazzarethMap dalla quale erano stati rimossi 304 cubi provvisori. Il pacchetto iniziale e il primo LEGGIMI erano in:

`C:\Users\12700K RTX3070Ti\Documents\Codex\2026-09-27\sai\outputs`

Sono stati sviluppati terreno, strade e perimetri a partire da dati moderni. Nella Panoramica sono presenti **1.016 attori stradali con 9.715 punti iniziali**, larghezze e quote modificabili.

- Corso Vittorio Emanuele II usa la mesh **Lavica_curved** e il materiale della spline stradale di Comune.
- Le altre strade hanno finiture provvisorie; nel campione sette spline hanno ricevuto pietra consumata o cemento riparato. Cinque larghezze iniziali da 1,8 m sono state portate a 3 m nella sola copia campione, come proposta da rifinire.
- Larghezza complessiva in metri, Scale Y dei punti per larghezze locali, punti e tangenti modificabili.
- La città di lavoro è già stata riflessa rispetto a Y=0: **`(X,Y,Z) → (X,−Y,Z)`**. Non applicare un secondo ribaltamento. Per nuove importazioni leggere `coordinate_frame.json`, poiché alcuni file generati più vecchi usano ancora il sistema precedente.
- Le mesh corrette usano scala positiva; evitare di introdurre scale negative per correggere nuovamente la città.
- Il difetto delle strade a triangolo era causato da **direzioni nulle nei punti CurveClamped**, non dalla forma della mesh lavica. Il generatore usa ora direzioni ricavate dai punti vicini quando necessario.
- La cache problematica delle spline è stata disattivata con `r.SplineMesh.SceneTextures=0`; non riattivarla senza una prova mirata e un salvataggio preventivo.
- Comune, Matrice e San Domenico sono stati collocati in prima posa. Dieci strutture personali sono raccolte nel Catalogo; le altre richiedono collocazione e allineamento.

Quote del DSM moderno, larghezze, incroci, marciapiedi, scalinate e proporzioni delle strutture personali richiedono ancora revisione locale e riscontro storico. La questione FOV/proporzioni della Matrice non va risolta alterandone arbitrariamente la scala sulla base di una sola immagine.

## 4. Generatore attuale delle case

Plugin locale: **MazzarinoRoads**. Classe nativa: `AMazzarinoHistoricBuilding`; Python: `unreal.MazzarinoHistoricBuilding`.

Sorgenti:

- `D:\UE5Projects\GameAnimationSample\Plugins\MazzarinoRoads\Source\MazzarinoRoads\Public\MazzarinoHistoricBuilding.h`
- `D:\UE5Projects\GameAnimationSample\Plugins\MazzarinoRoads\Source\MazzarinoRoads\Private\MazzarinoHistoricBuilding.cpp`

Le 18 case sono tre esempi per ciascuna delle sei famiglie:

| Famiglia | Identificativi dei lotti |
|---|---|
| Casa bassa popolare | 1249069275, 1249069286, 1249069247 |
| Casa stretta su più piani | 1249069213, 1249069271, 1249069276 |
| Casa d'angolo | 1249069204, 1249069237, 1249069219 |
| Casa con piccolo cortile | 1249069205, 1249069228, 1249069202 |
| Casa ampliata in epoche successive | 1249069200, 1249069235, 1249069287 |
| Piccolo palazzetto | 1249068307, 1249069246, 1249069229 |

Il sistema crea volumi, pareti, aperture con profondità reale, coperture, balconi, persiane, gradini, canalette e dettagli quotidiani. Le scelte dipendono da famiglia, lotto e seed. Sono presenti corti, ali e sopraelevazioni; i perimetri importati rimangono il limite della costruzione.

La generazione precedente di **3.216 attori edilizi è stata eliminata soltanto dal campione**. Le mappe archiviate la conservano. Non eliminare il vecchio codice dal plugin: serve per aprire quelle mappe. I perimetri rimossi sono archiviati anche in `Saved/Mazzarino80/Historic/previous_lots.json`.

### Appoggio al terreno

Nell'editor l'aggiornamento controlla i supporti ogni secondo, anche con Realtime disattivato. La strada assegnata determina la quota d'ingresso; se il terreno al fronte è più alto, prevale il terreno. Le fondazioni seguono la superficie campionata. Pitch e roll vengono azzerati.

Il terreno deve fornire collisione per essere campionabile. Un grande dislivello richiede ancora la revisione di scale e muri di sostegno: l'automatismo non garantisce un ingresso comodo per qualunque modifica arbitraria. In gioco viene utilizzata la geometria salvata; non è stato realizzato un aggiornamento continuo degli edifici durante il gameplay.

## 5. Ultima rifinitura: cosa è stato effettivamente cambiato

L'utente aveva segnalato davanzali enormi, fili e pluviali rettangolari, tetti piatti/lineari, pareti non chiuse e balconi troppo semplici.

| Problema | Intervento applicato |
|---|---|
| Davanzali | Sporgenza esterna 5,5 cm, spessore 4,5 cm; corretta la relazione con la profondità dell'imbotte |
| Pareti aperte | Chiusura dei lati interni/esterni, estremità e fondi; mantenimento dei lati condivisi; corretta triangolazione dei contorni |
| Coperture | Falda e colmo variabili; modulo di coppo tridimensionale riutilizzabile e coppi sul colmo; superfici sottostanti chiuse |
| Balconi | Sezioni tonde, volute semplici, mensole sagomate, profili delle lastre; alcuni balconi completi di Comune |
| Cavi e pluviali | Spline reali modificabili, cavi con mesh di Comune, tubi tondi, curve terminali e staffe |
| Canalette | Sezione a U, griglie e materiale opaco separato, evitando la precedente frammentazione del materiale mascherato |
| Facciate | Cinque case in muratura a vista, tredici in calce consumata; UV continue per la pietra, finiture individuali |
| Materiale dei coppi | Argilla chiara/scura, depositi minerali e porosità moderata, variazione per istanza |

Conteggi attuali: **28.259 coppi**, **9 istanze di balcone completo**, **112 spline di cavi/pluviali**. Il coppo è modellato per il progetto, non è una scansione.

I balconi completi recuperati hanno balaustra in pietra e ferro; sono usati su alcune case curate, non rappresentano la soluzione tipica di tutte le abitazioni popolari.

## 6. Parametri e modifiche manuali da conservare

Restano esposti famiglia, seed, piani, altezza piano, spessore muri, varietà dei volumi, irregolarità facciate, densità balconi, degrado, cortile, sopraelevazione, appoggi, materiali e gruppi di visibilità.

Sono stati aggiunti:

- Sporgenza e spessore davanzali.
- Diametro pluviale 0,07 m, diametro cavo 0,012 m, freccia iniziale dei cavi 0,22 m.
- Mostra coppi, passo trasversale 0,20 m, passo longitudinale 0,36 m, irregolarità di posa.
- Mesh e materiale dei coppi; mesh cavo; mesh, abilitazione e calibrazione della larghezza del balcone completo.
- Materiale separato delle canalette.
- **Conserva spline cavi e pluviali modificate**, attivo.
- **Ripristina percorsi cavi e pluviali**, pulsante per ricreare solo gli impianti.

I punti degli impianti modificati dall'utente sopravvivono alla rigenerazione. Cambiare seed o freccia dei cavi non ridisegna i percorsi già conservati: usare il pulsante di ripristino soltanto se si vuole perdere il tracciato manuale. Non eseguire indiscriminatamente script che reimpostano tutti i parametri, materiali o seed delle case.

## 7. Risorse già disponibili

Le librerie copiate sono sotto:

- `/Game/Mazzarino80/Library/Comune`
- `/Game/Mazzarino80/Library/ComuneDetail`

L'ultima integrazione ha importato 29 pacchetti e dipendenze, senza dipendenze mancanti rilevate. Risorse principali:

- `SM_wire_part_01`, usata lungo l'asse X sulle spline dei cavi; `BP_Wires` di Comune è stato esaminato come riferimento.
- Megascans `Modular_Building_Balcony_ukjsdavdw`, usato in nove istanze.
- Megascans `Modular_Building_Roof_Kit_ukjsdfvdw`, cinque pezzi disponibili ma **non distribuiti** sulle case: comprendono coperture complete, non singoli coppi da stirare sui lotti.
- `Migrated/Balcony` e `Balcony2`, disponibili per future varianti ma da calibrare.
- Pietra, intonaco, legno consumato, coppi, portoni e vasi già recuperati.

Coppo creato: `/Game/Mazzarino80/Historic/Modules/SM_Coppo_siciliano`; sorgente OBJ in `Research/Mazzarino80/Modules/Coppo_siciliano.obj`.

Nessun pacchetto è stato acquistato o scaricato durante questa rifinitura. Prima di cercarne altri, esaminare ciò che Comune contiene già. Mancano soprattutto varianti architettoniche locali ben calibrate, non una libreria generica di edifici monumentali.

## 8. Verifiche concluse e limiti

**Verificato in Unreal, non soltanto nel codice:**

- Apertura, salvataggio e riapertura della mappa campione.
- Compilazione del plugin per Editor, gioco Development e Shipping.
- Rigenerazione deterministica; cambio di seed di una casa senza alterare le altre.
- 146.095 triangoli procedurali esaminati: zero triangoli degeneri, nessun errore di geometria riportato.
- Strada spostata di +80 cm: ingresso aggiornato e casa verticale. Terreno spostato di +60 cm: aggiornamento delle posizioni o fondazioni delle 18 case. Prove ripristinate.
- Perimetri: differenza massima XY 0 cm rispetto ai lotti precedenti.
- Punto di cavo modificato manualmente conservato dopo rigenerazione; prova ripristinata.
- Riapertura: conservati punti delle 112 spline, seed, numero di coppi e balconi, davanzali e verticalità.
- Render reali dalla strada, nel vicolo, panoramici, in grigio e dei dettagli.
- Salvataggio finale dei pacchetti modificati; `final_save.json` riporta zero pacchetti sporchi residui.

**Non ancora verificato o completato:**

- Giro completo in Play con il personaggio. Le prove di collisione con capsula su sette strade non lo sostituiscono. Due interferenze al centro di via Catania hanno un passaggio laterale possibile, da provare camminando.
- Prestazioni dell'intero paese. I coppi rappresentano circa 5,8 milioni di triangoli instanziati prima del culling: verificare LOD e costi prima dell'estensione a migliaia di edifici.
- Fedeltà storica delle singole case e delle quote nel 1980.
- Interni abitabili, balconi accessibili e percorsi completi attraverso gli edifici.
- Qualità finale delle facciate: molte superfici di calce sono ancora troppo pulite; coperture e bordi dei coppi troppo regolari rispetto alle foto.
- Allineamento definitivo di chiese, piazze e strutture personali.

Le strutture recuperate mantengono i materiali originali nelle immagini grigie: il controllo uniforme riguarda le 18 case del generatore.

## 9. Confronti, guide, rapporti e copie di sicurezza

Radice di tutti i percorsi relativi elencati qui: **`D:\UE5Projects\GameAnimationSample`**.

### Confronto attuale

- `Saved/Mazzarino80/Preview/Historic/Confronto_dettagli.html`: confronto interattivo prima/dopo nelle stesse camere, immagini intere e dettagli.
- `Saved/Mazzarino80/Preview/Historic/BeforeDetails`: render precedenti all'ultima rifinitura.
- `Saved/Mazzarino80/Preview/Historic/Details`: render attuali, compresi `detail_roof.png` e `detail_balcony.png`.
- `Refined` e `Confronto.html`: fasi precedenti; non confonderle con il risultato più recente.

La pagina era stata mostrata anche su `http://127.0.0.1:8768/Confronto_dettagli.html`. **Il collegamento funziona soltanto mentre il server locale è attivo**; il file HTML e le cartelle di immagini sono il riferimento durevole. Il cursore è stato verificato anche da tastiera.

### Guide

- `Research/Mazzarino80/LEGGIMI_CaseStoriche.md`, sezione finale della rifinitura attuale.
- `Research/Mazzarino80/LEGGIMI_StradeSpline.md`.
- `Research/Mazzarino80/Riferimenti_dettagli.md`: Street View e risorse esaminate.
- `Research/Mazzarino80/coordinate_frame.json`.
- Cataloghi delle risorse e strutture nella stessa cartella Research.

### Rapporti

In `Saved/Mazzarino80/Historic`: `validation.json`, `detail_validation.json`, `persistence.json`, `integrity.json`, `routes.json`, `step_passage.json`, `details.json`, `facade_finishes.json`, `final_save.json`.

### Copie di sicurezza

- `Saved/Mazzarino80/Backups/Before_detail_refinement_2026-09-28`: prima dell'ultima rifinitura, con mappa e sorgenti precedenti.
- `Saved/Mazzarino80/Backups/Before_sample_cleanup_2026-09-28`: campione prima dell'eliminazione della vecchia generazione.
- Altri backup di strade, ribaltamento Y, edifici e grammatica nella stessa cartella Backups.
- `Content/Levels/M80_Recovery_PreDetails_20260928_1728.umap`: salvataggio di recupero intermedio; **non è la mappa attuale**.

SHA256 delle mappe archiviate, verificati invariati alla fine della rifinitura:

```
MazzarethMap:
64B9F8A58710730F280A05473B72BB06E30665ADA67B067447E44D67D19A6541

Mazzarino80_Panoramica:
980F6973D6FD5DFB7AE8B1BACE63041F4D2D18D8A422A55F5E3363E4643A96E7
```

## 10. Indicazioni operative per la nuova chat

1. Leggere questo report e la sezione finale del LEGGIMI delle case.
2. Controllare quale mappa è aperta, che ci sia una sola istanza del progetto e se l'utente sta modificando la scena. Non chiudere una finestra con modifiche non salvate senza conservarle.
3. Aprire il **campione attuale**, guardare le ultime immagini e ispezionare un paio di case dalla quota del giocatore e dall'alto. Non ricreare da zero la fase precedente.
4. Conservare un nuovo backup prima di ulteriori modifiche al generatore o alle 18 case.
5. Scegliere le varianti dalla libreria Comune, calibrare pochi esempi e integrarli nella grammatica senza appiattire le sei famiglie.
6. Dopo modifiche concrete controllare forma, raccordi, materiali, rigenerazione della singola casa e persistenza dei dettagli manuali. Ripetere solo le verifiche pertinenti al rischio della modifica.
7. Salvare, acquisire confronti reali dalle stesse camere e aggiornare il report. Distinguere sempre ciò che è implementato da ciò che è stato effettivamente visto o provato in Unreal.

### Priorità della prossima rifinitura

**Prima: materiali e coperture.** Ridurre l'aspetto troppo bianco/pulito, migliorare pietra esposta e rappezzi, dare cause leggibili all'usura. Nei tetti introdurre variazioni credibili di posa, bordi, raccordi, gronde e coppi sostituiti; evitare l'effetto di file perfettamente identiche e superfici corrugate continue.

**Poi: balconi, aperture e ferramenta.** Aggiungere varianti di ringhiere in ferro e mensole delle case modeste; usare con misura i balconi in pietra. Diversificare portoni siciliani, archi semplici, persiane aperte/chiuse/usurate, aperture tamponate e davanzali. Conservare spessori e logica strutturale.

**Poi: rapporto con vicolo e terreno.** Rifinire gradini, ingressi a quote differenti, canalette, bordi, muri di sostegno e piccoli slarghi compatibili con la pianta reale. Non spostare arbitrariamente lotti o strade per ottenere una composizione pittoresca.

**Prima di estendere il paese:** prova in Play, controllo delle prestazioni, riduzione delle ripetizioni tra vicini, verifica delle strutture personali e approvazione visiva del campione da parte dell'utente. La richiesta attuale resta rifinire le 18 case.

### File operativi da conoscere, non da avviare tutti insieme

Gli script sono sotto `Scripts` e quelli basati su `unreal` vanno eseguiti nel contesto Python dell'editor.

- `mazzarino80_historic_apply_details.py`: assegna mesh, materiali e valori del campione; può sovrascrivere scelte manuali, quindi non usarlo come semplice verifica.
- `mazzarino80_historic_material_depth.py`: cinque finiture di muratura e tredici di calce; reimposta le assegnazioni del campione.
- `mazzarino80_historic_tile_finish.py`: ricostruisce il materiale dei coppi.
- `mazzarino80_historic_view.py`: selezione delle camere/modalità mediante `Saved/Mazzarino80/Historic/view_mode.txt`.
- `mazzarino80_historic_detail_cameras.py`: camere dei dettagli, con inquadratura del tetto già corretta per evitare l'occlusione da una parete vicina.
- `mazzarino80_historic_capture_details.py`: serie completa di render e ripristino finale della vista del vicolo.
- `mazzarino80_historic_capture_finish.py`: aggiornamento delle sole viste a colori interessate dai materiali.
- Verifiche mirate: `mazzarino80_historic_validate.py`, `mazzarino80_historic_validate_details.py`, `mazzarino80_historic_integrity.py`, `mazzarino80_historic_routes.py`, `mazzarino80_historic_step_passage.py`.
- `mazzarino80_historic_persistence.py`: salva e riapre la mappa, confronta impianti e moduli; eseguirlo solo quando la riapertura è pertinente e lo stato è stato salvato.
- `mazzarino80_historic_save_final.py`: salva i pacchetti modificati sotto Mazzarino80 e il campione, registrando i residui.
- `mazzarino80_detail_gallery.py`: ricrea la pagina di confronto da immagini reali già esportate; non modifica Unreal.

### Compilazione e problemi risolti

Il sorgente nativo aggiornato e l'ambiente di compilazione conservato sono in:

`Saved/M80BuildingPluginBuildV14/HostProject/Plugins/MazzarinoRoads`

Gli ultimi aggiornamenti sono stati compilati incrementalmente nel **HostProject**. Non considerare automaticamente aggiornati i binari del pacchetto esterno alla sottocartella HostProject.

I DLL installati sotto `Binaries/Win64` e `Plugins/MazzarinoRoads/Binaries/Win64` coincidono, con hash finale:

`5D3969C5D1BFDD4BE2E4F3F4723AE3F5F1245BC9E60F96AFA0F99BDECA3F893D`

Sono presenti anche gli intermedi precompilati per gioco Development e Shipping. Dopo cambiamenti al C++ compilare e distribuire coerentemente il modulo; non sostituire DLL caricati da un editor aperto.

Problemi incontrati e risolti:

- Più editor aperti contemporaneamente bloccavano il salvataggio: conservato uno stato di recupero e chiuse le copie duplicate.
- Una prima versione di rotazioni delle mesh aveva quaternioni non normalizzati: corretti orientamento e normalizzazione; versioni finali verificate.
- L'esportatore TGA di UE 5.5 ha causato un arresto per `SupportsTexture(Texture)` durante l'esame di una texture. Il progetto salvato è stato riaperto. **Non rieseguire quell'esportazione**; lo script di ispezione è stato modificato per evitarla.
- Alcuni materiali delle strutture personali mostrano avvisi preesistenti su trasparenza/Nanite; non considerarli automaticamente difetti del nuovo generatore.

## 11. Testo da usare per avviare la nuova chat

> Continua il progetto Mazzarino anni Ottanta in `D:\UE5Projects\GameAnimationSample`. Leggi prima `D:\UE5Projects\GameAnimationSample\Research\Mazzarino80\REPORT_PASSAGGIO_CHAT_2026-09-28.md` e la sezione finale di `LEGGIMI_CaseStoriche.md`. Lavora sulla mappa `Mazzarino80_CaseStoriche_Campione`: rifiniamo ancora le 18 case, senza estendere il generatore al paese e senza ripristinare le case precedenti. Conserva perimetri, orientamento già corretto e strutture personali. Migliora soprattutto materiali, coppi, balconi, persiane e raccordi al terreno usando le risorse di Comune. Le case devono seguire terreno e spline restando verticali sullo Z globale. Verifica il risultato in Unreal e mostrami render prima/dopo, indicando ciò che resta da controllare.
