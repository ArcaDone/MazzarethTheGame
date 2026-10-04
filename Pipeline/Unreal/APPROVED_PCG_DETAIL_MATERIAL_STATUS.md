# PCG delle case storiche: materiali e dettagli, 2 ottobre 2026

La mappa approvata `/Game/Levels/Mazzarino80_CaseStoriche_Campione` e i suoi
18 edifici restano intatti. Il kit delle quattro case Blender non sostituisce
pareti, volumi o coperture. La prova corrente usa il catalogo approvato da
37.037 punti in `Research/Mazzarino80/PCG/BakedSource/approved_modules.json`.

## Materiali candidati

`/Game/Mazzarino80/PCG/SurfaceMaster/` contiene due grafi PBR condivisi con
lo stesso schema: `M_M80_PCG_Surface` e `M_M80_PCG_Surface_VT`. Il secondo e
necessario per la texture dell'intonaco gia importata come Virtual Texture.
Le 21 istanze coprono pietra, sei varianti di calce, coppi 3D, tetti, legno,
ferro, vetro, laterizio e pavimentazioni. Superfici minerali: rugosita alta,
specularita bassa, rilievo attenuato e variazione cromatica macro discreta.
Le texture originali e i materiali esterni degli asset del catalogo restano.

Il catalogo candidato e in
`Research/Mazzarino80/PCG/Candidates/approved_detail_material_v1.json`.
Le referenze a materiali distinti scendono da 42 a 32, inclusi i materiali
esterni non consolidabili. I 18 lotti e tutti i 37.037 punti conservano
posizione, rotazione, scala, seed e mesh strutturali. Sono presenti soltanto
tre sostituzioni di bucato, sul lotto `1249069237`, come prova di dettaglio;
il loro attacco resta da controllare a vista. I balconi, i vasi, le porte e
gli altri dettagli gia presenti non sono duplicati. Pluviali, scale e tende
migrate da `Comune` restano candidati: non hanno ancora ancoraggi affidabili.

## Prova in Unreal

I 18 data asset e i 18 grafi candidati sono sotto
`/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/`. I grafi riusano il
master PCG in cinque fasi preesistente. La mappa separata
`L_CaseStoriche_DetailQA` e una copia del campione: quattro edifici pilota
sono collegati ai grafi candidati; le altre case restano alla versione
approvata. Nella copia, 9.531 istanze dei quattro piloti hanno ricevuto
l'anteprima dei materiali. La riapertura della mappa conferma tutte le
9.553 istanze attese, senza posizioni mancanti o aggiunte e senza materiali
attesi assenti. L'hash della mappa originale e rimasto invariato.

L'anteprima degli ISM e stata applicata anche direttamente nella **sola**
copia QA: il commandlet UE senza viewport programma la rigenerazione PCG,
ma chiude prima che il processo asincrono termini. Nell'editor grafico ho
eseguito Cleanup e Generate sul lotto `1249069204`, salvato la copia e
ricontrollato la mappa da disco: 3.466 istanze per quel lotto, con tutti i
materiali attesi e nessuna trasformazione mancante o aggiunta. Gli altri tre
piloti restano collegati ai grafi candidati ma hanno ancora l'anteprima ISM
applicata direttamente; la rigenerazione completa di ciascuno e il confronto
visivo da piu punti alla quota del manichino restano da fare. La vista
illuminata iniziale mostra pietra calda e opaca nella corte osservata, ma
quella corte non e uno dei quattro piloti e non e una convalida estetica del
kit. In altre viste restano evidenti bordi e basamenti chiari e una trama di
laterizi molto regolare: il master non risolve da solo UV o geometrie poco
rifinite. Anche le tre sostituzioni dei vestiti sono ancora da valutare nel
livello, perche il loro lotto non rientra nei quattro piloti della copia QA.
Non e stata ancora misurata la differenza di FPS/draw call con identica
inquadratura e impostazioni. La condivisione del grafo materiale semplifica
la manutenzione; non equivale automaticamente a meno draw call.

## Evidenze

- `approved_pcg_surface_audit.json`: inventario dei 42 materiali di partenza.
- `approved_pcg_surface_master_result.json`: i due master e le 21 istanze.
- `approved_pcg_detail_material_candidate_report.json`: invarianti geometrici e riduzione dei percorsi materiale.
- `approved_pcg_detail_candidate_assets_result.json`: 18 asset e grafi candidati.
- `approved_pcg_detail_material_qa_map_result.json`: copia QA e hash della sorgente.
- `approved_pcg_surface_preview_result.json`: 9.531 istanze con l'anteprima.
- `approved_pcg_detail_material_qa_verification.json`: confronto puntuale dei quattro piloti.
