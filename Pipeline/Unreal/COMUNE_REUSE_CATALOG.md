# Risorse da riusare dal progetto `Comune`

Audit del 30 settembre 2026, aggiornato il 1 ottobre 2026. Sorgente: `D:\UE5Projects\Comune\Content`;
destinazione: `D:\UE5Projects\GameAnimationSample\Content`.

## Migrazione selettiva verificata (1 ottobre)

Sono stati promossi `SM_Clothes_01`, `SM_Clothes_03` (Favela/Mannequin),
`SM_Old_Stair_01`, `SM_Rain_Pipe_01` (Favela) e `SM_awning_01` (MiddleEast).
La chiusura delle dipendenze comprende 33 pacchetti: 25 file nuovi copiati,
otto pacchetti condivisi gia presenti conservati. In UE 5.5 tutti e 33 si
caricano e nessun riferimento `/Game` risulta mancante. I dettagli sono in
`comune_migration_plan.json`, `comune_migration_result.json` e
`comune_migration_validation.json`.

Il confronto delle sagome e in `comune_geometry_review/`. I vestiti
`MiddleEast/SM_clothes_A_02..05` e `B_01/B_03` sono sostanzialmente pannelli;
`B_02` e un drappo largo circa 1,78 m, non un capo. Le varianti Favela hanno
sagome riconoscibili. `SM_Water_Pipe_01` misura circa 22,6 x 26,6 x 15,6 m:
non e un pluviale adatto alla casa. Il pannello di ringhiera MiddleEast e i
balconi di oltre 5 m non aggiungono una soluzione migliore delle ringhiere gia
presenti. `SM_awning_01` e largo 4,38 m: usarlo solo sul fronte commerciale
dello stile 03 dopo controllo a quota uomo. La scala Favela e il pluviale
restano candidati visivi, pur avendo passato la verifica tecnica.

## Gia presenti nel progetto attuale

Tutti i **681 asset** in `Comune/Content/Migrated` hanno una copia allo stesso
percorso relativo in `GameAnimationSample/Content/Migrated`. Tra questi:

- `Balcony`, `Balcony2`, `Case/Door/Porta*`, `Case/Tetto`;
- `Arinazzo/Pot*`, `Madonna/gateway*` e altri pezzi architettonici;
- materiali e texture gia usati dagli asset migrati.

Nel pacchetto `Megapack/Meshes/MiddleEast` sono gia presenti almeno
`SM_metal_gate_01`, `SM_wooden_gates_01`, `SM_clothes_A_01` e alcune porte.
Due varianti dell'edera inglese sono gia in
`Mazzarino80/Library/Comune/Megascans/3D_Plants/English_Ivy_rkEit`.
Prima di creare o migrare un oggetto, verificare questi asset nel livello
campione e confrontarli con i moduli Blender.

## Candidati ancora in `Comune`

| Esigenza | Asset da valutare | Stato |
|---|---|---|
| Vestiti riconoscibili | `Megapack/Blueprints/MiddleEast/BP_prefab_clothes_01`, `BP_prefab_clothes_2`; `Meshes/MiddleEast/SM_clothes_A_02..05`, `SM_clothes_B_01..03`; `Meshes/Favela/Mannequin/SM_Clothes_01..03` | Favela `01` e `03` migrati; le sagome MiddleEast sono state scartate per il campione |
| Balconi e inferriate | `Megapack/Meshes/MiddleEast/SM_balcony_01..02`, `SM_Windows_grill_01..02`, `SM_metal_fence_01` | Da confrontare con `Balcony2` e il balcone corretto nel kit Blender |
| Tende e aperture | `Megapack/Meshes/MiddleEast/SM_awning_01`, `SM_awning_base_01`, `SM_awning_cloth_01`, `SM_window_01`, `SM_Window_02` | `SM_awning_01` migrato come candidato per lo stile 03, da verificare in scena |
| Pluviali, scale, corte | `Megapack/Meshes/MiddleEast/SM_Water_Pipe_01`, `SM_stairs_01`; `Meshes/Favela/SM_Rain_Pipe_01`, `SM_Old_Stair_01..02`, `SM_Metal_Fence_01..02` | `SM_Rain_Pipe_01` e `SM_Old_Stair_01` migrati; elementi MiddleEast fuori scala esclusi |
| Legno usurato | `Megapack/Meshes/MiddleEast/SM_wooden_beams_01..05`, `SM_wooden_pallet_01` | Candidati per listelli, puntelli e riparazioni |
| Verde | `Megascans/3D_Plants/English_Ivy_rkEit` (altre varianti) e `Esercitazioni/FoliageCasaFloresta_` | Usare pochi esemplari, istanze e LOD; sono gia presenti due mesh di edera |
| Manifesti e segni urbani | `Decals_mazza` (31 asset) | Cartella assente nel progetto attuale; da valutare prima della migrazione |

Non conviene migrare pacchetti interi: per i candidati promossi, usare **Migra**
da Unreal per includere le dipendenze e conservare i percorsi delle risorse.
Le copie manuali di singoli `.uasset` possono perdere riferimenti a materiali,
texture e blueprint. Il progetto `Comune` dichiara UE 5.4; il progetto corrente
dichiara UE 5.5. Verificare i candidati nel progetto di destinazione dopo la
migrazione e non sovrascrivere alla cieca le copie gia presenti.
