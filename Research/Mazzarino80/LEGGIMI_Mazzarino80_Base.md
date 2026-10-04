# Mazzarino80_Base — prima modifica del progetto

> Nota: questo è il resoconto della copia iniziale. Gli interventi successivi nel progetto su `D:` sono registrati in [STATO_2026-09-27.md](STATO_2026-09-27.md).

## Aprire la mappa

La nuova mappa si chiama **`/Game/Levels/Mazzarino80_Base`**. È una copia di `MazzarethMap`; `MazzarethMap`, `MazzarethMap1` e la mappa iniziale `Main` non sono stati modificati.

Per inserirla nel progetto su `D:\UE5Projects\GameAnimationSample`, chiudere Unreal Editor e fare doppio clic su `Installa_Mazzarino80_Base.cmd`, tenendolo nella stessa cartella dello ZIP. Lo script verifica il percorso e installa soltanto la nuova mappa; si ferma se la mappa esiste già. In alternativa, estrarre `Mazzarino80_Base_unreal.zip` nella cartella principale del progetto, conservando le cartelle `Content` contenute nello ZIP. Poi aprire il progetto e la mappa `Content/Levels/Mazzarino80_Base` dal Content Browser. Lo ZIP contiene solo file nuovi, senza sostituire quelli della mappa originale.

La stessa mappa è già presente nella copia di lavoro del progetto in `C:\Users\12700K RTX3070Ti\Documents\Codex\2026-09-27\sai\work\GameAnimationSample`. Le modifiche non sono state scritte direttamente nel progetto su `D:` perché l'accesso in scrittura a quella cartella non è stato concesso in questa sessione.

## Modifiche verificate

| Contenuto | Originale | Nuova mappa |
|---|---:|---:|
| Attori | 345 | 41 |
| Cubi provvisori autonomi | 304 | 0 |
| Proxy del Landscape | 16 | 16 |
| Strutture architettoniche nominate | 10 | 10 |
| Grandi piani di riferimento | 2 | 2 |

I 304 cubi autonomi sono stati rimossi dalla copia. Ho conservato i due piani, denominati `Plane` e `Plane2`, perché sono superfici grandi diversi dai cubi provvisori. Ho conservato anche i due piccoli componenti Cube interni al Blueprint `A_Salesiane`: fanno parte di un asset architettonico e richiedono un controllo visivo prima di modificarli. La mappa è stata riaperta in Unreal Engine 5.5 e salvata senza errori; l'inventario successivo conferma l'assenza dei 304 cubi.

## Riferimenti già presenti

Coordinate locali Unreal, in metri; la quota è **relativa al progetto**, non una quota geografica assoluta. Questi dieci punti sono censiti, ma la loro corrispondenza con coordinate geografiche va ancora confermata.

| Oggetto | X | Y | Z |
|---|---:|---:|---:|
| ComuneCompleto | 485,06 | -33,18 | 161,50 |
| A_ZzaRita | 723,54 | 12,61 | 166,89 |
| A_Liardo | 254,08 | 55,59 | 155,07 |
| A_Madonna | 1168,52 | -58,27 | 181,04 |
| A_SanDomenico | 942,89 | -23,26 | 171,35 |
| ScuolaMatrice | 860,25 | 15,13 | 173,27 |
| CastelCompleted | 650,83 | -748,18 | 176,00 |
| Matrice | 823,74 | -40,06 | 171,13 |
| A_Salesiane | 167,09 | 116,40 | 157,59 |
| A_Agip | 215,81 | 57,15 | 156,89 |

Le chiese, il castello, il Comune e diversi edifici hanno già mesh esterne riutilizzabili. I Blueprint includono spesso piazze, alberi e arredi: il punto di origine del Blueprint non è necessariamente il centro dell'edificio. Per questo non ho ancora traslato o riscalato l'intera mappa usando soltanto due chiese come ancore.

## Verifica preliminare del terreno

Ho campionato il Landscape con tracce di collisione in **1681 punti**, su una griglia di 25 m che copre un'area centrale di 1 × 1 km. La differenza massima di quota relativa va da 0 a 195 m. Su 3280 coppie di punti adiacenti, **790** mostrano una differenza di quota superiore alla distanza orizzontale di 25 m. Questo conferma che nella mappa ci sono estesi salti o pareti ripide. Non dimostra che ciascuno di essi tagli una strada: per stabilirlo occorre sovrapporre una rete pedonale storicamente verificata e controllare il percorso alla quota del personaggio.

`Mazzarino80_verifica_terreno.png` mostra la distribuzione delle quote e dei salti. `Mazzarino80_campioni_terreno.csv` contiene i campioni per controlli successivi.

## Fonti geografiche e certezza

`Mazzarino_OSM_strade_chiese_2026.geojson` contiene **1134 elementi** esportati da OpenStreetMap il 27 settembre 2026: strade, percorsi pedonali, scalinate e chiese nel rettangolo di studio. Sono un **riferimento attuale**, non una prova della configurazione del 1980. Dati © contributori [OpenStreetMap](https://www.openstreetmap.org/copyright), licenza ODbL. Attribuire OpenStreetMap se questi dati vengono usati in materiali distribuiti.

Per la ricostruzione degli anni Ottanta servono prima le fonti datate della Regione Siciliana:

- [Riprese 1977–79](https://www.sitr.regione.sicilia.it/riprese-aereee/volo-anni-1977-78-79/): il volo copre circa due terzi della Sicilia; la copertura effettiva di Mazzarino resta da verificare sui fotogrammi.
- [Riprese 1988–89](https://www.sitr.regione.sicilia.it/riprese-aereee/dati-volo-italia-anni-1988-89/): controllo successivo, da usare dichiarando la differenza di data.
- [Carta tecnica regionale](https://www.sitr.regione.sicilia.it/download/download-carta-tecnica-2000/cart2000-pdf/): supporto per misurare strade e isolati, da distinguere in base all'anno del rilievo.
- La [sezione CTR 638070, intitolata «Mazzarino»](https://www.sitr.regione.sicilia.it/wp-content/uploads/Documenti/Download-Cartografia/ctr_2012_2013/pdf/ATA2012_638070.pdf), identifica il foglio moderno da cui partire per rintracciare le edizioni precedenti.
- [Modello del terreno a 2 m](https://www.sitr.regione.sicilia.it/geoportale/it/metadata/details/945): deriva da un rilievo del 2012–13 ed è utilizzabile come confronto delle quote, con controllo delle modifiche successive al 1980.

Il sito delle riprese storiche non ha risposto durante questa sessione; non ho potuto verificare la copertura di Mazzarino né acquisire i fotogrammi. La cartografia OSM **non è stata importata come geometria definitiva** nella mappa.

## Lavoro ancora necessario per la base percorribile

1. Ottenere le riprese storiche e definire il perimetro dell'abitato dei primi anni Ottanta.
2. Corrispondere almeno dieci punti di controllo fra riprese, carta tecnica e asset già collocati; misurare scala, rotazione e scostamenti.
3. Individuare sulla mappa le strade effettivamente presenti nel 1980 e verificare dove i salti di quota attraversano un percorso pubblico.
4. Correggere localmente terreno, muri di sostegno, rampe e scalinate. La priorità è un percorso campione Comune–Matrice–San Domenico, con un vicolo in pendenza e gli isolati adiacenti.
5. Proseguire quartiere per quartiere con impronte e altezze degli edifici, poi verificare in Play ogni strada pubblica a piedi.

**Stato:** la copia pulita e l'audit preliminare sono pronti. L'intero paese non è ancora ricostruito né certificato percorribile.
