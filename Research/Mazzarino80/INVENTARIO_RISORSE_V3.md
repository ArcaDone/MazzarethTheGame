# Inventario risorse per le case V3

Ricerca del 2 ottobre 2026 nei nomi degli asset di `D:/UE5Projects/Comune/Content` (Megapack, Megascans, OldWest) e del progetto. Quasi tutte le risorse utili esistono **solo in Comune**; nel progetto ci sono già alcune piante Megapack, i panni `SM_clothes_A_*`, il fico d'India e il cancello `SM_Metal_Gate_01`, ma dentro cartelle escluse da Git (`Content/Megapack`, `Content/Megascans`).

## Metodo di migrazione

1. Dall'editor di **Comune** (script Python): `AssetTools.migrate_packages` dei pacchetti sotto, destinazione `D:/UE5Projects/GameAnimationSample/Content` (mantiene i percorsi `/Game/Megapack/...`, con materiali e texture dipendenti).
2. Nel progetto: `EditorAssetLibrary.rename_asset` di mesh, materiali e texture usati verso `/Game/Mazzarino80/Kit/<gruppo>/` (versionata), poi riduzione texture a 2K/1K con sorgente JPEG (`UM80EditorLibrary`).
3. Gli stili (`UM80HouseStyle`) puntano solo a `/Game/Mazzarino80/Kit`.

## Piante e vegetazione

| Asset | Percorso in Comune |
|---|---|
| `S_English_Ivy_rkEit_Var1_lod1` | `/Game/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var1_lod1` |
| `S_English_Ivy_rkEit_Var5_lod1` | `/Game/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var5_lod1` |
| `S_English_Ivy_rkEit_Var9_lod1` | `/Game/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var9_lod1` |
| `S_Cactus_udugcc3fa_lod3_Var1` | `/Game/Megascans/3D_Assets/Cactus_udugcc3fa/S_Cactus_udugcc3fa_lod3_Var1` |
| `SM_Plant_01` | `/Game/Megapack/Meshes/Favela/Plants/SM_Plant_01` |
| `SM_Plant_05` | `/Game/Megapack/Meshes/Favela/Plants/SM_Plant_05` |
| `SM_Plant_10` | `/Game/Megapack/Meshes/Favela/Plants/SM_Plant_10` |
| `SM_Plants_01` | `/Game/Megapack/Meshes/Yakohama/SM_Plants_01` |

## Vasi

| Asset | Percorso in Comune |
|---|---|
| `SM_FlowerPots_01` | `/Game/Megapack/Meshes/Yakohama/SM_FlowerPots_01` |
| `SM_FlowerPots_04` | `/Game/Megapack/Meshes/Yakohama/SM_FlowerPots_04` |
| `SM_FlowerPots_07` | `/Game/Megapack/Meshes/Yakohama/SM_FlowerPots_07` |
| `S_Cactus_Pot_uenkeewfa_lod0_Var1` | `/Game/Megascans/3D_Assets/Cactus_Pot_uenkeewfa/S_Cactus_Pot_uenkeewfa_lod0_Var1` |
| `S_Flower_Pot_tlulehkva_lod3` | `/Game/Megascans/3D_Assets/Flower_Pot_tlulehkva/S_Flower_Pot_tlulehkva_lod3` |

## Tetti: antenne e cisterne

| Asset | Percorso in Comune |
|---|---|
| `SM_Antenna_01` | `/Game/Megapack/Meshes/Favela/SM_Antenna_01` |
| `SM_Antenna_02` | `/Game/Megapack/Meshes/Favela/SM_Antenna_02` |
| `SM_Antenna_03` | `/Game/Megapack/Meshes/Favela/SM_Antenna_03` |
| `SM_AntennaSupport_01` | `/Game/Megapack/Meshes/Favela/SM_AntennaSupport_01` |
| `SM_Water_Tank_01` | `/Game/Megapack/Meshes/MiddleEast/SM_Water_Tank_01` |
| `SM_Water_Tank_02` | `/Game/Megapack/Meshes/MiddleEast/SM_Water_Tank_02` |
| `SM_Platform_Water_Tank_01` | `/Game/Megapack/Meshes/MiddleEast/SM_Platform_Water_Tank_01` |
| `S_Rusty_Gas_Tank_udmkdejqx_lod3` | `/Game/Megascans/3D_Assets/Rusty_Gas_Tank_udmkdejqx/S_Rusty_Gas_Tank_udmkdejqx_lod3` |

## Fili e impianti

| Asset | Percorso in Comune |
|---|---|
| `SM_Wires_01` | `/Game/Megapack/Meshes/MiddleEast/SM_Wires_01` |
| `SM_Wire_01` | `/Game/Megapack/Meshes/Yakohama/SM_Wire_01` |
| `SM_wire_part_01` | `/Game/Megapack/Meshes/MiddleEast/Wires/SM_wire_part_01` |
| `SM_ElectricBox_01` | `/Game/Megapack/Meshes/Yakohama/SM_ElectricBox_01` |
| `SM_ElectricBox_02` | `/Game/Megapack/Meshes/Yakohama/SM_ElectricBox_02` |

## Lampioni

| Asset | Percorso in Comune |
|---|---|
| `SM_StreetLamp_02` | `/Game/Megapack/Meshes/Favela/SM_StreetLamp_02` |
| `SM_StreetLamp_05` | `/Game/Megapack/Meshes/Favela/SM_StreetLamp_05` |
| `SM_LampA_01` | `/Game/Megapack/Meshes/Favela/SM_LampA_01` |

## Negozi e bar

| Asset | Percorso in Comune |
|---|---|
| `SM_Awning_05` | `/Game/Megapack/Meshes/Yakohama/SM_Awning_05` |
| `SM_Awning_06` | `/Game/Megapack/Meshes/Yakohama/SM_Awning_06` |
| `SM_Awning_07` | `/Game/Megapack/Meshes/Yakohama/SM_Awning_07` |
| `SM_Awning_08` | `/Game/Megapack/Meshes/Yakohama/SM_Awning_08` |
| `SM_awning_01` | `/Game/Megapack/Meshes/MiddleEast/SM_awning_01` |
| `SM_Sign_03` | `/Game/Megapack/Meshes/Yakohama/SM_Sign_03` |
| `SM_Sign_05` | `/Game/Megapack/Meshes/Yakohama/SM_Sign_05` |
| `SM_Sign_08` | `/Game/Megapack/Meshes/Yakohama/SM_Sign_08` |
| `SM_Signboard_01` | `/Game/Megapack/Meshes/Yakohama/SM_Signboard_01` |
| `SM_SignText_01` | `/Game/Megapack/Meshes/Yakohama/SM_SignText_01` |
| `SM_Shelf_01` | `/Game/Megapack/Meshes/Favela/SM_Shelf_01` |
| `SM_Shelf_03` | `/Game/Megapack/Meshes/Favela/SM_Shelf_03` |
| `SM_Bottle_01` | `/Game/Megapack/Meshes/Yakohama/SM_Bottle_01` |
| `SM_Bottle_02` | `/Game/Megapack/Meshes/Yakohama/SM_Bottle_02` |
| `SM_Cardboard_box_01` | `/Game/Megapack/Meshes/MiddleEast/SM_Cardboard_box_01` |
| `SM_PlasticBox_01` | `/Game/Megapack/Meshes/Yakohama/SM_PlasticBox_01` |
| `SM_market_table_01` | `/Game/Megapack/Meshes/MiddleEast/SM_market_table_01` |
| `SM_Table_01` | `/Game/Megapack/Meshes/Favela/SM_Table_01` |
| `SM_TrashBox_02` | `/Game/Megapack/Meshes/Yakohama/SM_TrashBox_02` |

## Panni stesi

| Asset | Percorso in Comune |
|---|---|
| `SM_clothes_A_01` | `/Game/Megapack/Meshes/MiddleEast/SM_clothes_A_01` |
| `SM_clothes_B_01` | `/Game/Megapack/Meshes/MiddleEast/SM_clothes_B_01` |
| `SM_Clothes_01` | `/Game/Megapack/Meshes/Favela/Mannequin/SM_Clothes_01` |

## Cancelli e cortili

| Asset | Percorso in Comune |
|---|---|
| `SM_Metal_Gate_01` | `/Game/Megapack/Meshes/Favela/SM_Metal_Gate_01` |
| `SM_metal_gate_01` | `/Game/Megapack/Meshes/MiddleEast/SM_metal_gate_01` |
| `SM_wooden_gates_01` | `/Game/Megapack/Meshes/MiddleEast/SM_wooden_gates_01` |
| `S_Medieval_Iron_Gate_tjykeeofa_lod3` | `/Game/Megascans/3D_Assets/Medieval_Iron_Gate_tjykeeofa/S_Medieval_Iron_Gate_tjykeeofa_lod3` |

## Arredi per le stanze in parallasse

| Asset | Percorso in Comune |
|---|---|
| `SM_Bed_01a` | `/Game/OldWestAssets/OldWestVol1/VOL1/Meshes/SM_Bed_01a` |
| `SM_Table_01a` | `/Game/OldWestAssets/OldWestVol1/VOL1/Meshes/SM_Table_01a` |
| `SM_Chair_04a` | `/Game/OldWestAssets/OldWestVol5/VOL5/Meshes/SM_Chair_04a` |
| `SM_Cabinet_02a` | `/Game/OldWestAssets/OldWestVol1/VOL1/Meshes/SM_Cabinet_02a` |
| `SM_Wall_Shelf_01a` | `/Game/OldWestAssets/OldWestVol1/VOL1/Meshes/SM_Wall_Shelf_01a` |
| `SM_Stove_01a` | `/Game/OldWestAssets/OldWestVol5/VOL5/Meshes/SM_Stove_01a` |
| `SM_Barrels_01a` | `/Game/OldWestAssets/OldWestVol5/VOL5/Meshes/SM_Barrels_01a` |
| `SM_Crate_01a` | `/Game/OldWestAssets/OldWestVol5/VOL5/Meshes/SM_Crate_01a` |
| `SM_Lamp_01a` | `/Game/OldWestAssets/OldWestVol3/VOL3/Meshes/SM_Lamp_01a` |
