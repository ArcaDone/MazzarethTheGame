# Golden Standard operativo — campione 18

## Fonti e limiti

- Geografia: impronte e quote della mappa campione, nel sistema di coordinate già riflesso. I dati catastali/OSM moderni non certificano la forma del 1980.
- Stile: `D:/Blender/AssetsMazzarethTheGame/CaseSoluzione.blend`, aperto con Blender 3.3, e materiali/moduli già importati da `D:/UE5Projects/Comune`.
- Confronto visivo: render reali in `Saved/Mazzarino80/Preview/Historic/Details`; le case C++ correnti sono la soglia minima di qualità da superare.
- Le collezioni Blender contengono **tile e componenti**, non un catalogo pronto di 18 edifici interi. Non importare l'intera scena come casa.

## Cinque riferimenti selezionati

| Riferimento Blender | Funzione | Vincolo d'uso |
|---|---|
| `Ground` (`GroundFloorPopolari`) | muro e zoccolo popolare, modulo ~1 m | Riferimento per ritmo e spessore; mantenere appoggio alla strada. |
| `window.011` (`windowsPopolari`) | coppia di aperture semplici | Usare sulle case modeste, modulando l'interasse in base al fronte reale. |
| `RoofPopolari001` (`RoofPopolari`) | geometria di falda popolare | Adeguare alle impronte irregolari; completare con i coppi e materiali già presenti in Unreal. |
| `RoofCornerPopolari001` (`RoofPopolari`) | raccordo di copertura | Riservare agli spigoli compatibili, senza stirare la mesh sull'intero lotto. |
| `window.010` (`windowsPopolari`) | apertura con balcone leggero | Variante controllata sulle case a più piani; non ripeterla su ogni fronte. |

Le anteprime isolate sono in `Saved/Mazzarino80/PCG/Golden`. Sono render di controllo geometrico in Workbench, quindi **non** certificano texture e finitura finale. `Ground.014` mostra una saracinesca contemporanea e non entra nella grammatica di base del centro storico. `House.002` e `Balcony` non sono leggibili nelle viste isolate e non sono approvati come Golden Asset.

## Controllo di scala in Unreal

Nella mappa di validazione `/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext`, davanti al lotto `1249069202`, sono presenti `Reference_Mannequin_180cm_1249069202` e `Reference_ExactHeight_180cm_1249069202`. Manny è a scala 1 e misura 180,997 cm nell'asset; l'asta accanto misura esattamente 180 cm. Servono per valutare dalla quota del giocatore porte, davanzali, balconi e altezza di ciascun piano. Sono riferimenti di lavoro, non elementi delle case o della mappa campione finale. La persistenza dopo salvataggio e riapertura è registrata in `Saved/Mazzarino80/PCG/scale_reference_reopen.json`; la vista è in `Saved/Mazzarino80/PCG/CharacterPilot_1249069202.png`.

## Regole per i moduli PCG

Unreal usa centimetri: convertire le dimensioni metriche Blender moltiplicando per 100. Per ciascun modulo impiegato fissare pivot, asse avanti, asse alto, scala positiva, collisione e materiali prima della distribuzione. Preferire le mesh e le istanze già nel progetto, inclusi `SM_Coppo_siciliano`, i balconi calibrati, le texture di Comune e le finiture individuali delle 18 case. Un modulo nuovo deve risolvere una lacuna verificata del kit. Le variazioni di intonaco, pietra, legno e coppi devono restare compatibili con le immagini delle case popolari abitate dei primi anni Ottanta; i balconi monumentali sono eccezioni.
