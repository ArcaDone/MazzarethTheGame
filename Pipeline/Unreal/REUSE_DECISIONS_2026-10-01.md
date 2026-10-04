# Selezione degli asset per i quattro stili

Decisione del 1 ottobre 2026. Il campione Blender e l'audit degli asset Unreal
sono le fonti tecniche; la promozione visiva finale richiede il confronto dei
quattro provini a quota uomo con `stili.png`.

| Uso | Asset | Decisione |
|---|---|---|
| Facciate in pietra, porte e infissi | `B80__Ground.*`, `B80__Porta4/6`, `CS__wall_004/010/011/012` nel kit Blender | Base dei provini 01 e 04; per 02 e 03 cambiare la finitura della muratura. Le tessere `CS` restano candidate: scala originaria 1 m, portata a 3 m. |
| Tetto a coppi, comignolo | `B80__Tetto`, `B80__tegole`, `B80__small_chimney_*` | Riutilizzare; correggere la stesura in profondita del tetto per evitare coppi allungati. |
| Balcone ornamentale | `PILOT__KIT_Balcony_StoneAndIron_350` | Solo campione visivo: 3,5 × 1,2 m, 63.782 facce. Serve versione alleggerita per ripetizioni PCG. |
| Balconi gia in Unreal | `/Game/Migrated/Balcony`, `Balcony2` | Alternative da confrontare: larghezza 2,56/3,89 m, Nanite attivo, due slot Megascans 4K. Non distribuirli su ogni facciata senza misure. |
| Piante murali | `EVY__Ivy_Instance_*_WALL` | Usare l'orientamento a muro gia corretto, non il cespo da tetto. Le grandi mesh da 10 M facce del file sorgente restano escluse. |
| Cancello corte | `/Game/Megapack/Meshes/MiddleEast/SM_metal_gate_01`, `SM_wooden_gates_01` | Gia disponibili: 3,40 × 3,12 m e 2,91 × 3,47 m. Confrontare contro la variante Blender `FENCE__Cast Iron Fence 09_LOD1`, ancora priva di cardini. |
| Vestiti | `SM_clothes_A_01` e altri `Comune/Megapack` | `A_01` e gia presente e ha sagoma 0,57 × 0,84 m. Migrare `A_02..05`, `B_01..03` e i tre `Favela/Mannequin/SM_Clothes` solo dopo confronto; scartare pannelli rettangolari. |
| Pluviali, scale, travi | `Comune/Megapack/Meshes/MiddleEast/SM_Water_Pipe_01`, `SM_stairs_01`, `SM_wooden_beams_01..05`; `Favela/SM_Rain_Pipe_01`, `SM_Old_Stair_01..02` | Candidati da migrare con dipendenze e verificare a terra e sul muro. |
| Decal e cartelli | `Comune/Content/Decals_mazza` | Tenere fuori dal primo import; scegliere solo gli elementi che rafforzano il periodo storico. |

`Comune/Content/Migrated` contiene 681 asset gia presenti allo stesso percorso
nel progetto corrente. Non occorre una seconda copia. Per gli asset ancora
assenti usare la migrazione Unreal con dipendenze, non copiare singoli `.uasset`.

Le quattro abitazioni prodotte in precedenza in `stylized_pilots_v1` non
superano il confronto visivo: sono volumi di prova e **non sono sorgenti da
importare**. Il nuovo confronto modulare e in
`Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/`.

Il passaggio ai grafi PCG resta vincolato a tre verifiche: silhouette e materiali
dei quattro stili, rapporto con manichino 1,80 m, e controllo di pivot/attacchi
dei singoli moduli. Le misure di riferimento del catalogo dei lotti in Unreal
sono altezze piano di 2,70–3,06 m.
