# Mazzarino 80

Gioco open world nello stile di GTA e Red Dead Redemption 2, ambientato a **Mazzarino (Caltanissetta) negli anni '80**. Il paese è ricostruito sui dati reali: terreno, strade ed edifici di OpenStreetMap. Le case sono generate in modo procedurale con lo stile delle case siciliane dell'entroterra.

Progetto Unreal Engine **5.8** (dal 14 ottobre 2026; l'ultima versione in 5.5 è il tag Git `ue55-final`, l'inizio della migrazione è `pre-ue58`): `MazzarethTheGame.uproject`, nato dal Game Animation Sample.
Repository privato: `ArcaDone/MazzarethTheGame` (Git + LFS).

- **Dove si va:** [`Research/Mazzarino80/PIANO_GTA.md`](Research/Mazzarino80/PIANO_GTA.md) (fasi, traguardi, cosa è fatto e cosa manca).
- **Dove siamo:** questo file.

---

## 1. Aprire il progetto

| Cosa | Dove |
|---|---|
| Motore | Unreal 5.8.3 in `D:\UE_5.8` (Visual Studio 2026 per il C++) |
| Compilare (editor chiuso) | `D:\UE_5.8\Engine\Build\BatchFiles\Build.bat MazzarethTheGameEditor Win64 Development -Project="D:\UE5Projects\GameAnimationSample\MazzarethTheGame.uproject"` |
| Mappa d'apertura | `/Game/Levels/Main`: vuota, si apre in pochi secondi |
| **Mappa del paese** | `/Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP` (World Partition) |
| Modalità di gioco | "Mazzarino 80 (gioco)" (`M80GameMode`), predefinita del progetto |

**La mappa del paese è in World Partition.**
- Ogni attore (casa, strada, lampione…) è un file a sé in `Content/__ExternalActors__/…/L_M80_Paese_WP`.
- La mappa si apre vuota in 3 secondi.
- Per lavorare su una zona: finestra *World Partition* → selezioni le celle → *Load Region from Selection*. Caricare i 250 m intorno al Corso richiede circa 50 secondi; tutto il paese pesa molto di più.
- Atmosfera, orizzonte e zone di esclusione sono sempre caricati.
- In gioco le zone si caricano da sole intorno al giocatore. Da lontano si vedono gli **HLOD**: versioni semplificate delle case.
  - Si ricostruiscono dall'editor con *Build → Build HLODs* (circa 1 ora e 15 la prima volta, poi rifà solo quelli cambiati) o con il comando qui sotto, a editor chiuso.
  - Il build legge l'attore **salvato**: dopo aver cambiato un Blueprint di un edificio, risalva anche gli attori piazzati, se no l'HLOD non si aggiorna.
  - Gli edifici con componenti *Movable* non entrano negli HLOD (da lontano spariscono): i Blueprint degli edifici devono essere *Static*.
  - **Non si versionano** (oltre 700 MB a ogni ricostruzione): restano in locale e nel backup.
  - I loro file sono elencati in `.git/info/exclude`.

```
"D:\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UE5Projects\GameAnimationSample\MazzarethTheGame.uproject" /Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP -run=WorldPartitionBuilderCommandlet -Builder=WorldPartitionHLODsBuilder -AllowCommandletRendering
```

Altre mappe:
- `Houses/Maps/L_M80_Houses18_V2`: 18 case di prova del generatore.
- `Vehicles/L_M80_ProvaGuida`: pista di prova delle auto (rettilineo, rampe, slalom, vicolo). Tab cambia auto.
- `Player/Maps/L_M80_ProvaAzione`: il quartiere più fitto del paese (44 case vive) per provare armi e arrampicata. Si apre in pochi secondi. Contiene armi a terra, una Fiat 500, blocchi da 1, 2,2 e 2,9 m e quattro bersagli umani. Si rifà da zero con `m80_prova_azione_setup.py`.
- `Vehicles/Maps/L_M80_ProvaCarretti`: i quattro carretti a cuscinetti su un piano di basolato, con una piattaforma di 3 m e una rampa al 10% (la pendenza delle strade del paese) e uno slalom di paletti. Si rifà da zero con `m80_carretti_prova_setup.py`.
- `Rooms/L_M80_RoomStudio`: le stanze fotografate per le finestre.
- `L_M80_District_V2`: quartiere di prova, solo in locale.

### Comandi in gioco (tastiera / gamepad)

| Azione | Tasti |
|---|---|
| Mirare / sparare | Destro / sinistro del mouse; LT / RT. Mirando la camera va sopra la spalla destra. Con il gamepad LT aggancia la persona più vicina davanti. |
| Ruota delle armi (come GTA V) | Tenere Tab / LB: il tempo rallenta, mouse o stick destro scelgono il settore. Rotella, Q o X cambiano arma dentro il settore; lasciando il tasto si prende. Solo le armi raccolte, il resto resta vuoto. |
| Armi | 1-4 settore, Q o croce destra/sinistra arma successiva, R / X ricarica, G / croce giù lascia l'arma. |
| Saltare e arrampicarsi | Spazio / A. Davanti a un ostacolo di 0,5-2,5 m (muretto, auto, balcone basso) ci sale sopra. Più in alto (cornicioni, balconi, davanzali, tetti) salta e si aggrappa al bordo. |
| Appeso | Sinistra/destra lungo il bordo; Spazio / A sale sopra se c'è posto, oppure salta al bordo più in alto, oppure si stacca dal muro (indietro + salto). C, Ctrl o B si lascia cadere. |
| Auto, mappa, pausa | E / Y sale o scende (sulle auto a quattro ruote con l'animazione: apre, si china, si siede; scende dal lato guida); M mappa; P / Start pausa con la mappa del paese. |
| Sedie | E / Y vicino a una sedia (tag `M80Sedia`) ci si siede; E di nuovo ci si alza. Sedie, tavoli e carte di `L_M80_ProvaFolla` sono oggetti fisici: si spostano urtandoli a piedi o in auto. |
| Carretti | E / Y sale o scende. W / RT spinge (piano, al massimo 13 km/h), in discesa va da solo. S / LT frena coi piedi; da fermo lo fa arretrare. A / D sterzano, Spazio i talloni a terra. |
| Motorino (Piaggio Si) | E / Y sale da sinistra (gamba sopra la sella) o scende; se è a terra prima lo rialza. W / RT gas, S / LT freno; da fermo S lo spinge indietro coi piedi (niente retromarcia). Fermo, il piede sinistro va a terra. In curva si piega secondo velocità e raggio. Maiusc / X impennata: il pilota si sporge avanti e tira indietro, poi è fisica (il gas la tiene, il freno la abbassa, troppo gas e si ribalta). Contro un muro o ribaltato si vola via e ci si rialza. |

L'arrampicata funziona su qualsiasi geometria, perché cerca i bordi sulla collisione complessa. Non servono marcature sulle case.

---

## 2. Com'è fatto

### Plugin (C++, in `Plugins/`)

| Plugin | Contenuto |
|---|---|
| `MazzarinoHouses` | Generatore delle case e attrezzi per il paese |
| `MazzarinoRoads` | Strade a spline (dati OSM) e vecchi edifici a perimetro |
| `MazzarinoVehicles` | Auto Chaos guidabili, livello e GameMode di prova guida |
| `MazzarinoGameplay` | Giocatore, HUD, armi, vita, atmosfera, orizzonte, lampioni |

### Attori da trascinare nella mappa (Place Actors, cerca il nome)

| Nome | A cosa serve |
|---|---|
| **Casa Mazzarino (procedurale)** | Una casa o una schiera su un perimetro a spline chiusa. Il pannello *Casa* ha stile, piani, finitura, degrado, tetto, schiera, terreno, "Vissuto", negozi e bar per lato, dettagli siciliani. Pulsanti *Rigenera* e *Rigenera con i vicini*. |
| **Isolato da riempire** | Disegni il perimetro di un isolato con una spline chiusa e premi *Genera case*: crea una schiera tutto intorno con un cortile al centro (profondità, piani, stile, seed). *Elimina case generate* le toglie. Serve per riempire le zone dove OSM non ha case. |
| **Zona senza case procedurali** | Perimetro a spline: le case con il centro dentro spariscono, per lasciare posto agli edifici fatti a mano (Matrice, Comune, Poste…). Spegnendo o spostando la zona le case tornano. |
| **Strada Mazzarino (spline)** | Strade OSM (1016): larghezza, quote, pavimentazione. Sul landscape le strade sono dipinte (layer "Strada"); le spline servono da guida a case, marciapiedi e lampioni. |
| **Marciapiede** | Spline con lastra e cordolo in pietra lavica: aperto, ad anello o piazza piena. La lastra è una mesh unica posata sul terreno ogni 50 cm ai due bordi (segue le pendenze lungo e di traverso), con i fianchi in pietra lavica. Prova: `m80_marciapiede_prova.py`; per rifare quelli del paese `m80_marciapiedi_ricostruisci.py`. |
| **Scalinata** | Spline per gradini, cordonate e scalinate (anche in curva, in salita o in discesa) in pietra lavica e basolato, piene fino a terra o a soletta, con pianerottoli, muri laterali e staccionate (ferro battuto, tubolare, legno, canne). Prova: `L_M80_ProvaScalinate` (`Scripts/m80_stairs_setup.py`). |
| **Strada (Mazzarino)** | Spline per strade che si appoggiano al terreno come i marciapiedi e si inclinano di lato col pendio. *Superficie*: Lavica principale (`LowPoly`), Lavica bombata (`Lavica_curved`), Lastra con materiale (default `MI_M80_Lavica_secondaria`, mappata in metri) o mesh personalizzata. Le mesh si ripetono a pezzi proporzionati. Prova: `L_M80_ProvaScalinate`, cartella *Strade* (`Scripts/m80_road_setup.py`). |
| **Fili tra le case** | Cavi elettrici che attraversano la strada tra case vicine. |
| **Lampione (Mazzarino)** | Tipo *Muro* (lanterna esagonale a braccio) o *Palo* (candelabro in ghisa a tre luci). Modellati in Blender dalle foto dei lampioni veri. Si accendono da soli al tramonto. Opzioni *Spento (guasto)* e *Modello* per cambiare mesh. |
| **Atmosfera (Mazzarino)** | Sole nella posizione reale per Mazzarino (latitudine, giorno dell'anno, ora), luna, cielo, nuvole, foschia nelle valli, ora blu, notte. Meteo: Sereno, Afa estiva, Scirocco, Nuvoloso. In gioco l'ora avanza. |
| **Orizzonte (colline ed Etna)** | Anello di colline lontane con il profilo dell'Etna. |
| **Auto Mazzarino** | Fiat 500 F, Mini Cooper S, Maggiolino, Golf GTI, BMW M3: modelli scaricati, **non decimati** (la 500 ha 242 mila triangoli, le altre 36-85 mila), un solo LOD (`m80_auto_sorgente.py`, `m80_fiat500_sorgente.py`, `m80_prepare_vehicle.py`). Poi Ape e Vespa. 126, Panda, 127, Uno e la Golf vecchia tolte il 16/10/2026: troppo pesanti per il traffico. |
| **Piaggio Si (guidabile)** | Il motorino (`D:\Mazzarino80_Sorgenti\Auto\Piaggio_Si`): 49 cc, circa 47 km/h, sterzo sull'asse inclinato della forcella, pugni sulle manopole. Al posto della Vespa, tolta il 18/10/2026. Mappa di prova `Vehicles/Maps/L_M80_ProvaMoto`. |
| **Carretti** | *Carretto a cuscinetti* (sdraiati sul petto, mani sulla barra davanti), *a triangolo* e *con la cassetta* (seduti come in un go-kart, talloni sull'asse, corda in mano), *persiana* (seduti, braccia sul manico di scopa come su un chopper). Niente motore: si spingono piano e corrono in discesa (circa 22 km/h in fondo a 30 m al 10%). |
| **Bouganvillea (Mazzarino)** | Pianta procedurale che cresce lungo una spline. Regole d'uso nella sezione qui sotto. |
| **Negozi di una casa** | Nella casa, sezione *Negozi*: per ogni negozio il lato (premi *Mostra numeri dei lati*; -1 = facciata principale), il prototipo (`/Game/Mazzarino/Prototipi`: Alimentari, Bar Sport, Tabaccheria, Frutta, Ferramenta, Farmacia, Abbigliamento, Edicola, Officina, Negozio chiuso) e la posizione lungo il lato. Quel tratto del piano terra diventa una stanza vera aperta sulla strada, arredata con le regole del pacchetto, con una luce debole e calda. |
| **Strade per la navigazione** | Una per mappa col traffico: la parte centrale delle strade costa ai pedoni, che restano lungo le case e attraversano dove serve. |
| **Parcheggio (Mazzarino)** | Stallo: le auto degli NPC a fine giro ci parcheggiano e il guidatore scende. |

### La bouganvillea (spline)

**Come si disegna:**
- La spline è il **fusto principale**. Il primo punto è la radice: mettilo a terra, a qualche centimetro dal muro, mai dentro.
- Disegna il fusto lungo il percorso che vuoi: su per un muro, lungo un balcone o un cornicione, su un palo, o attraverso la strada fino alla casa di fronte.
- I rami nascono da soli e si regolano solo con i parametri. Dal fusto escono i rami, dai rami i rametti.

**Come cresce:**
- I rami non attraversano mai muri e oggetti: ci si appoggiano e ci scivolano sopra. Per questo servono le collisioni (case, balconi e terreno le hanno).
- **Rampicante** acceso: i rami restano attaccati alle superfici e ricadono oltre gli spigoli. Spento: è un cespuglio libero.
- **Colore**: magenta, viola, arancione o rosso, uguale per tutta la pianta. **Variante (seed)** cambia la forma a parità di parametri.

**Regole per le strade:**
- **Passaggio libero**: i rami che pendono nel vuoto si fermano a questa altezza sopra la radice. Le piante sui muri usano 2,2 m, quelle che attraversano la strada 4 m.
- Per attraversare una strada: fusto teso tra le due facciate ad **almeno 4,7 m** sopra il punto più alto del suolo sotto (strada e soglie), più basso dei due muri, senza balconi o fili in mezzo. Accendi **Filo di sostegno**: disegna un cavo sotto il fusto nei tratti che non toccano niente.

**Parametri:**

| Gruppo | Cosa regola |
|---|---|
| Rami | raggio del tronco, tronco nudo alla base, rami per metro, lunghezza, livelli (1-3), apertura, ricadenza, irregolarità |
| Foglie e fiori | quantità di foglie e di fiori, fiori verso le punte, dimensioni, foglie piegate (più belle da vicino, il doppio dei triangoli) |
| Rampicante | distanza di presa, distacco dal muro |

**Peso:**
- Una pianta su un cubo di 1,5 m sono circa 25.000 triangoli. Lo script del paese tiene ogni pianta sotto i 40.000.
- Foglie e brattee sono card trasparenti (2 triangoli) prese dagli atlanti 2×2 delle texture.

**Cottura e HLOD:**
- `unreal.M80EditorLibrary.bake_bougainvillea(pianta, "/Game/Mazzarino80/Vegetazione/Bouganvillea/Piante")` trasforma la pianta in una Static Mesh con tre LOD fatti a mano: da lontano tiene meno card, ma più grandi. Così entra negli HLOD.
- Qualsiasi modifica la riporta in anteprima finché non la ricuoci.
- Come le case, le mesh cotte sono **fuori da Git**: lo script del paese le ricuoce. Se manca la mesh cotta, la pianta si rigenera da sola.

**Script:**

| Script | Cosa fa |
|---|---|
| `m80_bouganvillea_materiali.py` | Texture (da `D:\Mazzarino80_Sorgenti\Vegetazione\Bouganvillea`) e materiali in `Vegetazione/Bouganvillea`: card con trasparenza, vento, traslucenza, corteccia. |
| `m80_bouganvillea_paese.py` | Mette le piante nel 5% delle case, vicino a un angolo della facciata principale dove il muro è pieno (non davanti a porte o vetrine). Dove una casa ha un muro di fronte a 2,5-13 m, metà delle piante attraversa la strada con le regole sopra. Ogni pianta viene cotta e salvata da sola. Si può rilanciare: salta le case che hanno già una pianta e ricuoce quelle senza mesh. Variabili: `M80_BGV_QUOTA`, `M80_BGV_PASSAGGI`, `M80_BGV_TRIANGOLI`, `M80_BGV_CENTRO`, `M80_BGV_FOTO=1` (foto dalla strada), `M80_BGV_PROVA=1` (non salva). |
| `m80_bouganvillea_prova.py` | Quattro piante di prova lontano dalle case (cubo, sfera, cespuglio, muro) con le foto. |

Dopo aver aggiunto o spostato piante, ricostruisci gli HLOD (capitolo 1).

### Le case
- Ogni casa è una mesh generata dal C++ (anteprima live).
- Per la versione finale si **cuoce** in una Static Mesh Nanite, con `Scripts/m80_houses_bake.py`. Le mesh cotte vanno in `Content/Mazzarino80/Houses/Baked/…`: circa 900 MB, **fuori da Git**, si rigenerano.
- Qualsiasi modifica riporta la casa in anteprima finché non la ricuoci.
- **Stili** (`Content/Mazzarino80/Houses/Styles`):
  - 01 popolare in pietra
  - 02 palazzo urbano
  - 03 intonacata anni '50-'70
  - 04 casa povera

  Ogni stile contiene materiali, regole di facciata, liste di piante e oggetti.
- **Master material** `M_M80_HouseMaster`: texture senza ripetizioni (hex tiling), macchie, colature, umidità di risalita, intonaco che cade, muschio, palette di colori per casa.
- **Dettagli:**
  - piante, vasi, antenne, cisterne, panni stesi;
  - capochiave, tende a listarelle, case abbandonate;
  - ceramiche siciliane: teste di moro, pigne, graste, edicole votive, numeri civici;
  - targhe con i nomi veri delle vie, cartelli stradali, manifesti d'epoca.

  Sono istanze leggere, senza collisione, che spariscono oltre i 60 m (le piante oltre i 90 m).
- **Finestre con stanze in parallasse:** cucine, camere, negozi e bar fotografati in cubemap, accesi di notte.
- Oltre alle case procedurali il paese ha edifici fatti a mano: Matrice, Comune, palazzi neoclassici e le Poste importate da Blender.

### Cartelle utili

| Cartella | Contenuto |
|---|---|
| `Content/Mazzarino80/Houses` | Mappe, stili, materiali e mesh cotte delle case |
| `Content/Mazzarino80/Kit` | Oggetti versionati: piante, cartelli, ceramiche siciliane, lampioni, marciapiedi |
| `Content/Mazzarino80/Vegetazione` | Bouganvillea: texture, materiali e (fuori da Git) le mesh cotte delle piante |
| `Content/Mazzarino80/Vehicles`, `Player`, `Weapons`, `UI`, `Sky`, `Audio` | Gioco |
| `Scripts/` | Automazione dell'editor (Python) |
| `Tools/` | Backup, mappa del radar, suoni, migrazione dal progetto Comune |
| `Research/Mazzarino80/` | Dati OSM, terreno, piani, script Blender (`Blender/`) |

`Megapack`, `Megascans`, `Migrated` e gli altri pacchetti del marketplace sono **fuori da Git**: sono nel backup e nel progetto `D:\UE5Projects\Comune`.

---

## 3. Script di automazione

Gli script Python girano in un editor lanciato apposta:

```
powershell -ExecutionPolicy Bypass -File Scripts/run_editor_script.ps1 -Script Scripts/<script>.py [-ForceLit]
```

- **Mai con l'editor già aperto:** due editor sul paese esauriscono gli 8 GB della scheda video.
- `-ForceLit` serve per le foto: se lasci la vista in *Unlit*, la mette in *Lit* durante lo script e poi la rimette com'era.
- Nella mappa World Partition gli script caricano solo la zona che serve, a riquadri. Gli aiuti stanno in `Scripts/m80_seq.py` (`actor_descs`, `load`, `tiles`, `save_all`).
- I report finiscono in `Saved/Mazzarino80/…`, le foto in `Saved/Mazzarino80/Foto`.

| Script | Cosa fa |
|---|---|
| `m80_houses_bake.py` | Cuoce le case non ancora cotte, riquadro per riquadro. Report con le case fallite. |
| `m80_houses_district.py` | Crea le case dai lotti OSM, saltando quelli coperti da edifici fatti a mano. |
| `m80_town_zones.py` | Zone di esclusione attorno agli edifici fatti a mano, sul loro perimetro reale visto dall'alto (`m80_footprints.py`). |
| `m80_town_roads.py`, `m80_town_sidewalks.py`, `m80_town_props.py` | Strade dipinte, marciapiedi, cartelli e manifesti. |
| `m80_signs_setup.py`, `m80_street_wires_setup.py` | Targhe delle vie e cartelli; fili tra le case. |
| `m80_town_streetlights.py` | Lampioni a muro ogni 28 m lungo le strade, a lati alterni, il 5% guasti. |
| `m80_atmosphere_setup.py` | Piazza Atmosfera e Orizzonte. |
| `m80_atmosphere_photos.py`, `m80_town_aerial.py`, `m80_photos.py` | Foto a ore e meteo diversi; viste aeree. |
| `m80_profile_scene.py` | Misura fps, GPU, draw call e tempo di caricamento. |
| `m80_termometro.py` | Il "termometro" del paese: tempo di apertura della mappa e di Play fino a quando ci si muove, poi fps, GPU, draw call, RAM e memoria video in tre punti (partenza a mezzogiorno, piazza Matrice e panorama alle 20:30). Report e foto in `Saved/Mazzarino80/Termometro/<versione>_<data>`; serve a confrontare versioni del motore e a vedere quanto pesa ogni aggiunta. |
| `m80_memoria.py`, `m80_wp_analisi.py` | Dove va la memoria: attori caricati per classe e `memreport -full` dopo l'apertura del paese e durante Play (`Saved/Mazzarino80/Memoria`, `Saved/Profiling/MemReports`). Come è diviso il paese per World Partition: per classe quanti attori, quanti sempre caricati, dimensioni e distanza dal PlayerStart. |
| `m80_matrice_ispeziona.py`, `m80_matrice_place.py`, `m80_matrice_test.py` | La Matrice nuova (MatriceDentroFuori.blend, esterno e interno): com'era quella recuperata, posa della nuova sullo stesso posto (quella vecchia resta nascosta), prova di gioco dalla piazza fino alla navata. |
| `m80_hlod_ispeziona.py` | Perché un edificio fatto a mano manca (o è a metà) negli HLOD: per ogni attore grande non procedurale, layer HLOD, nascosto in gioco, mobilità e mesh dei componenti (gli HLOD scartano i componenti Movable e gli attori nascosti). Report in `Saved/Mazzarino80/Memoria/hlod_ispeziona.json`. |
| `m80_edifici_static.py` | Rende Static i Blueprint degli edifici recuperati (Madonna, Scuola della Matrice, Salesiane, Liardo, Castello, San Domenico, Matrice), così entrano negli HLOD; mostra la Matrice recuperata (con le mesh nuove) e nasconde il doppione `Matrice_Interno`. Poi vanno ricostruiti gli HLOD. |
| `m80_props_nanite.py`, `m80_town_hlod_setup.py` | Nanite sui dettagli; impostazione degli HLOD. |
| `m80_lamps_setup.py`, `m80_sicilia_setup.py`, `m80_import_blender_assets.py` | Import dei modelli da Blender (lampioni, ceramiche, edifici, veicoli). |
| `m80_play_test.py`, `m80_weapons_test.py`, `m80_vitals_test.py`, `m80_drive_telemetry.py`, `m80_cars_damage_test.py` | Test automatici in gioco con foto e report. |
| `m80_prova_azione_setup.py` | Rifà da zero la mappa di prova `L_M80_ProvaAzione`. |
| `m80_combattimento_test.py`, `m80_arrampicata_test.py` | Test in `L_M80_ProvaAzione`, con foto dalla camera del giocatore e di lato. Il primo prova mira, pose delle armi, errore della canna, ruota, pugni, aggancio e bersagli. Il secondo prova la salita sull'auto e sui blocchi, l'aggrappo, lo spostamento lungo il bordo, la salita sul tetto e la caduta. |
| `m80_weapons_setup.py` | Importa le armi da Blender (`M80_ARMI=Fucile` per importarne solo alcune), i materiali dei colpi e le animazioni ALS per rialzarsi. |
| `m80_carretti_import.py` + `Blender/m80_carretti_gioco.py` | I carretti di `D:\Mazzarino80_Sorgenti\Carretti` (Blender 5.2) con lo scheletro guidabile e la posa del guidatore per ciascuno; import in `Vehicles/Carretti` e `Player/Anim`. |
| `m80_motorino_import.py` + `Blender/m80_motorino_gioco.py` | Il Piaggio Si (Blender 5.2): scheletro guidabile (`Steer` lungo l'asse della forcella, `Sella`, `Mano_L/R`, `Piede_L/R`), materiali dalle texture del Si, le clip del pilota (guida, salita, discesa, raccolta da terra); import in `Vehicles/PiaggioSi` e `Player/Anim`, piazzato in `L_M80_ProvaGuida` e `L_M80_ProvaAzione`. |
| `m80_prova_moto_mappa.py`, `m80_motorino_test.py`, `m80_motorino_test_breve.py` | Piazzale di prova per le due ruote (muro a 80 m, marciapiede) e i test: completo (salita, piega, piede a terra, discesa, retro coi piedi, impennate, muro, marciapiede) e breve (gomiti e mani fotogramma per fotogramma, caduta dopo l'urto, raccolta). |
| `m80_carretti_prova_setup.py`, `m80_carretti_test.py` | Mappa di prova dei carretti e test: salita, foto, mani e piedi sui punti di presa, spinta, sterzo, freno, retromarcia, rampa, discesa. |
| `m80_animazioni_import.py` | Animazioni Mixamo (aggrappo, salita, pugni) e pose ALS di pistola e fucile, retargettate sul manichino del sample. |
| `m80_icone_armi.py` + `Blender/m80_icone_alpha.py` | Icone grigie delle armi per la ruota, fotografate di lato. |
| `m80_vito_crea.py` | Vito diventa un MetaHuman modificabile della 5.8 (`Personaggi/Vito/MHC_Vito`): il viso si adatta ai vertici di testa, occhi e denti del suo DNA, letto dal progetto Comune. Il DNA del vecchio Creator online non passa l'import diretto della 5.8 (rig diverso). |
| `m80_prova_folla_setup.py` | Rifà da zero la mappa di prova della folla `Personaggi/Maps/L_M80_ProvaFolla`: case vere attorno a una piazza lastricata, tavoli con sedie e carte siciliane, sedie impagliate davanti alle porte e i punti dove mettere la gente (tavolo, sedia, gruppi, giro della piazza, gioco dei bambini). |
| `m80_folla_sonda.py` | Cosa offre il MetaHuman Creator della 5.8: preset (altezza, corporatura, se hanno il rig), vestiti e capelli, pipeline normali e della folla. |
| `m80_folla_animazioni.py` + `Blender/m80_mixamo_folla.py` | Le clip Mixamo della folla (`D:\Mazzarino80_Sorgenti\Animazioni\Mixamo_Folla`) sul loro scheletro, retargettate sul manichino: camminate, chiacchiere, cadute, rialzarsi, investimento, salire e scendere dall'auto, sedersi, stare seduti, alzarsi. |
| `m80_folla_auto.py`, `m80_folla_sedie.py` | Parcheggiano le 5 auto nella piazza di `L_M80_ProvaFolla`; rendono fisici sedie, tavoli e carte (tag `M80Sedia`, `M80Tavolo`). |
| `m80_folla_azioni.py` | Prova in Play di quello che fa la folla, con foto: mani, anziani, caduta, investimento, sedia, guida, pugni (difesa o fuga), spavento per uno sparo, il giocatore che si siede e che entra/esce dall'auto, sedie spinte (`M80_AZIONI=...` per farne solo alcune). |
| `m80_negozi_prototipi.py` | I `prototipo_*.json` dei pacchetti dei negozi diventano gli asset `DA_Negozio_*` che le case usano nei *Negozi*. |
| `m80_prova_matrice.py` | Mappa di prova del traffico `Traffico/Maps/L_M80_ProvaMatrice`: la Matrice e 150 m intorno copiati da `L_M80_Paese_WP` (si rifà da capo e segue le modifiche del paese), il terreno rifatto con le stesse quote e le strade dipinte, la navigazione, auto che girano, folla, negozi. `M80_SOLO_TRAFFICO=1` rifà solo auto e parcheggi, `M80_SOLO_NEGOZI=1` solo i negozi (con foto). |
| `m80_prova_matrice_test.py` | Prova in Play del mini-paese: per 3 minuti registra cosa fa ogni auto e quanti pedoni sono in mezzo alla strada o aspettano sul bordo; foto dietro le auto e degli attraversamenti. |
| `m80_negozi_import.py` | Importa i pacchetti di `D:\Mazzarino80_Sorgenti\Interni_e_Negozi` (Kit Bottega, Bar Sport, Tabaccheria, Edicola, Cabina SIP) con i loro script e li dispone nella mappa di prova `Negozi/Maps/L_M80_ProvaNegozi`. Le lampade dei pacchetti al 15% dei loro lumen e calde (2800 K); `M80_SOLO_LUCI=1` rifà solo le luci. |

I circa 220 script `mazzarino80_*.py` sono della prima versione basata su PCG (settembre 2026): restano solo come archivio e non servono più.

### Modelli da Blender
- Gli script stanno in `Research/Mazzarino80/Blender/`. Producono FBX e texture dipinte o cotte con Cycles: lampioni, ceramiche siciliane, cartelli, armi, occhiali, tuta.
- Si lanciano con `blender -b --factory-startup --python <script>.py`.
- Poi si importano in Unreal con lo script `m80_*_setup.py` corrispondente.
- **Motorino:** `m80_motorino_gioco.py` (Blender 5.2) + `m80_motorino_import.py`. Le clip di salita e discesa si suonano col pilota attaccato al motorino (origine sulla `Sella`); le mani e i piedi del corpo MetaHuman vanno sui punti di presa dopo il retarget (`UM80BodyAnimInstance`).
- **Carretti:** `m80_carretti_gioco.py` (Blender 5.2) + `m80_carretti_import.py`. Ossa: `Steer` (asse o manico che sterza), ruote, `Sella` (dove va l'origine del giocatore), `Mano_L/R` e `Piede_L/R` (polsi e caviglie, figli di `Steer` se tengono lo sterzo).
- **Veicoli:** `m80_prepare_vehicle.py` + `m80_import_blender_assets.py`. Vanno rispettati i nomi delle ossa delle ruote, l'orientamento e la scala in cm, altrimenti Chaos si rompe. Auto scaricate: prima `m80_auto_sorgente.py <chiave> <fbx> <blend>` (scala 1:100 → vera, materiali rinominati), poi le stesse due; `"budget": 0` = niente decimazione, `"wheel_names"` se le gomme sono fatte di tanti pezzi.
- **Sorgenti:** tutti i file importati stanno in `D:\Mazzarino80_Sorgenti`, divisi per tipo (vedi il suo `LEGGIMI.md`). I file nuovi vanno messi lì.

---

## 4. Git e LFS

- Commit piccoli, uno per argomento, con push uno alla volta. In `git add` vanno sempre i percorsi espliciti, mai `commit -a`.
- La quota LFS gratuita è di **10 GB**: oggi ne usiamo circa 5,7.
- Della mappa del paese si versionano solo i file degli attori cambiati.
- Sono **fuori da Git**:
  - le mesh cotte delle case e delle bouganvillee;
  - gli HLOD;
  - i pacchetti del marketplace;
  - l'Ape (324 MB);
  - `Saved`, `Intermediate`, `DerivedDataCache`, `Binaries`.
- La vecchia storia (95 commit, fino al 4 ottobre 2026) è in `.git_old`: 38 GB, solo in locale.

---

## 5. Backup e trasferimento su un altro PC

Script: `Tools/Backup/MTGBackup.ps1`.

### Backup giornaliero
- L'attività pianificata di Windows **MTGBackup** lo lancia ogni giorno alle 13:00 e copia tutto in `C:\MTGBackup`.
- Salva il progetto in cui si trova lo script (o quello dato con `-Project`), in `C:\MTGBackup\GameAnimationSample_UE<versione>`: la 5.8 va in `GameAnimationSample_UE5.8`. I backup della 5.5 restano in `C:\MTGBackup\GameAnimationSample`, così le due versioni non si mischiano.
- Copia solo i file nuovi o cambiati e **non cancella mai nulla**: un file eliminato per sbaglio su D: resta recuperabile qui.
- Cosa copia:
  - il progetto, senza `.git`, cache, `Binaries` e `Intermediate`;
  - `Saved/Autosaves` e `Saved/Mazzarino80` (report, foto, copie delle mappe);
  - il progetto `D:\UE5Projects\Comune`;
  - tutti i sorgenti in `D:\Mazzarino80_Sorgenti` (anche i file Blender storici che stavano in `D:\Blender\AssetsMazzarethTheGame`, spostati il 17/10/2026), più le immagini ricevute in chat (in `Saved/Mazzarino80/Riferimenti`);
  - `D:\HDRI` e `D:\Audio_Music`;
  - gli appunti di Claude Code sul progetto (in `ClaudeMemory`, da rimettere in `C:\Users\<utente>\.claude\projects\D--UE5Projects-GameAnimationSample\memory`).
- Lanciarlo a mano (meglio con l'editor chiuso):
  ```
  schtasks /Run /TN MTGBackup
  ```
- Su un disco esterno:
  ```
  powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Dest E:\MTGBackup
  ```
- I log stanno in `<destinazione>\_logs`. Ogni log finisce con `FINISHED … - OK` oppure `WITH ERRORS`.

**Attenzione:** il backup giornaliero conserva anche i file cancellati, quindi **non va usato per spostare il progetto**. Con World Partition, gli attori eliminati ricomparirebbero nella mappa come doppioni.

### Copia per trasferimento (`-Transfer`)
Una copia pulita, identica a D:, da portare su un altro PC:

```
powershell -ExecutionPolicy Bypass -File Tools\Backup\MTGBackup.ps1 -Transfer -Dest E:\MTGBackup
```

- Scrive in `<Dest>\Trasferimento\` con la stessa struttura di D:
  - `UE5Projects\GameAnimationSample`
  - `UE5Projects\Comune`
  - `Mazzarino80_Sorgenti`
- È uno **specchio**: quello che non c'è più su D: viene tolto anche dalla copia (solo dentro `Trasferimento`). Le volte successive copia solo le differenze.
- Include `.git` con i file LFS (circa 5,4 GB): sull'altro PC il repository funziona subito, senza clonare.
- Include anche le **Binaries** già compilate dei plugin.
- Esclude cache, `Intermediate`, `Saved` e `.git_old`.
- Se l'editor è aperto si rifiuta di partire. Il log è `_logs\transfer_<data>.log`.
- Peso indicativo: circa 45 GB il progetto e circa 100 GB il progetto Comune.

Sull'altro PC:
1. Copia `UE5Projects` e `Blender` nella radice di **D:**, così tornano gli stessi percorsi di qui.
2. Installa Unreal **5.8**, possibilmente in `D:\UE_5.8`, e Git con Git LFS.
3. Apri `MazzarethTheGame.uproject`.
   - Con le Binaries incluse e lo stesso Unreal 5.8 si apre senza compilare.
   - Se chiede di ricompilare i moduli serve **Visual Studio 2026** con "Sviluppo di giochi con C++".
4. La prima apertura è lenta, da una a qualche ora: ricompila gli shader. Poi va normale.
5. Per rifare gli HLOD usa il comando del capitolo 1.

---

## 6. Cosa abbiamo fatto (in breve)

| Periodo | Lavoro |
|---|---|
| 27-28 set 2026 | Terreno reale (Copernicus 30 m), strade OSM a spline, città ribaltata sull'asse Y per farla combaciare col posto. Prima versione delle case con PCG (18 case campione), poi abbandonata. |
| 1-2 ott | Generatore di case **V2** in C++ (plugin `MazzarinoHouses`) con stili e master material. **V3 "vissuto" alla RDR2**: piante, antenne, fili, terrazzi, cortili, scale, negozi e bar, stanze in parallasse, case abbandonate, cartelli e targhe, ceramiche siciliane. |
| 3 ott | Paese `L_M80_Paese` con tutte le case cotte; edifici fatti a mano con zone di esclusione; strade dipinte, marciapiedi, manifesti, palazzi neoclassici. Auto guidabili (Chaos), pista di prova, giocatore MetaHuman in tuta acetata, HUD con radar. |
| 4 ott | Terreno ritoccato a mano. Storia Git azzerata (repository nuovo, circa 4,9 GB di LFS). Piano GTA. Armi, vita e morte, danni e fuoco delle auto, 7 veicoli. |
| 6 ott | Tutti i lotti OSM; zone sui perimetri reali degli edifici fatti a mano; strumento **Isolato da riempire**. **Atmosfera** con sole reale, notte, ora blu e Etna all'orizzonte. **World Partition** (la mappa si apre in 3 s invece che in 5 minuti), dettagli più leggeri, Nanite, HLOD. **Lampioni** dalle foto vere: 941 a muro. Backup con copia per trasferimento. |
| 12 ott | Bouganvillea procedurale a spline nel paese. **Combattimento e arrampicata** (punto 1 del piano GTA) nella mappa `L_M80_ProvaAzione`: camera sopra la spalla, pose delle armi di ALS con la canna sul mirino, ruota delle armi come GTA V, fucile da caccia, combo di pugni, aggancio con il gamepad, bersagli umani, arrampicata su muri, balconi, tetti e auto. |
| 12 ott (sera) | **Carretti a cuscinetti** guidabili: quattro modelli da Blender, ognuno con la sua posa del guidatore (sdraiato, go-kart, chopper) e mani e piedi che seguono lo sterzo; spinta lenta, discesa per gravità; mappa `L_M80_ProvaCarretti`. |
| 13-14 ott | **Passaggio a Unreal 5.8.3** (per MetaHuman Creator nell'editor e le prestazioni): copia di prova, stessi test e misure di 5.5 e 5.8. Griglia di World Partition del paese a celle di 64 m caricate fino a 192 m: Play pronto in 136 s invece di 229, 58-76 fps invece di 49-68, 10 GB di RAM in meno. Gli edifici recuperati (Madonna, Scuola, Salesiane, Liardo, Castello, San Domenico, Matrice) resi *Static* per vederli negli HLOD. |
| 16-17 ott | **Folla** in `L_M80_ProvaFolla`: 21 MetaHuman vestiti anni '80 che camminano (anziani curvi col bastone, anziane, borse), chiacchierano, si siedono sulle sedie, inciampano e si rialzano, vengono investiti, si difendono o scappano, scappano dagli spari, si scansano dalle auto, prendono le auto parcheggiate e le guidano. Il giocatore si siede e sale/scende dalle auto con l'animazione. Sedie e tavoli fisici. Quattro auto nuove non decimate (Mini, Maggiolino, Golf GTI, BMW M3) e la 500 rifatta. Marciapiedi che seguono il terreno. Sorgenti riuniti in `D:\Mazzarino80_Sorgenti`. Pacchetti dei negozi importati (`L_M80_ProvaNegozi`). |
| 18 ott | **Piaggio Si** al posto della Vespa: motorino guidabile da Blender con le sue texture, piega in curva secondo velocità e raggio, sterzo sull'asse della forcella; salita e discesa da sinistra con le clip fatte in Blender, piede a terra da fermo, retro coi piedi, impennata a fisica, urti che fanno volare il pilota; mani e piedi di Vito sul corpo MetaHuman dopo il retarget (niente più sfarfallio dei gomiti). |

---

## 7. Punti aperti

- **Macchia nel cielo** nelle viste aeree molto alte: sembra un difetto delle nuvole, non dell'orizzonte. Ancora da capire.
- **Zona delle Salesiane**: OSM non ha case nel triangolo. Si riempie a mano con *Isolato da riempire*.
- **Candelabri a tre luci**: da piazzare a mano nelle piazze.
- Due "case" OSM (lotti 1249067262 e 1249081252) sono triangoli di 0,6 m²: errori dei dati, non generano nulla.
- Il vaso `SM_M80_PROP__PottedPlant_Small_01` risulta modificato in locale da prima del 6 ottobre: decidere se tenerlo.
- `.git_old` (38 GB) va spostato o cancellato quando non serve più.
- **Paese buio di notte da lontano** con la griglia nuova: i lampioni lontani non sono caricati. Tenerli sempre caricati costa troppo (3 fps): da rivedere.
- **DynamicMesh in Play: 2,5 GB di RAM** (691 oggetti, 5.8 con la griglia nuova; erano 6,7 GB in 5.5). Le producono case non cotte, strade, marciapiedi, scalinate, fili, orizzonte e bouganvillea. Prima misurarle per tipo, poi cuocere in static mesh chi pesa di più. Da fare prima di portare la folla nel paese.
- **Ape: 974 mila triangoli**: va alleggerita prima di avere traffico. La 500 non decimata ne ha 242 mila (richiesta dell'utente: niente decimazione sulle auto scaricate).
- **Traffico** (mini-paese della Matrice, 17/10): corsie ricavate dalle strade OSM (a destra; incroci e stradine strette un'auto alla volta), adattate allo spazio libero tra cordoli e muri; le auto si fermano per pedoni e auto davanti e sorpassano quelle parcheggiate; i pedoni restano lungo le case e aspettano sul bordo. Da migliorare: alcune auto si incastrano ancora nelle curve strette o contro gli spigoli; parcheggi solo dove la strada è abbastanza larga (nel mini-paese nessuno). Da portare nel paese vero quando si sceglierà il senso di marcia.
- **Motorino senza pilota** (18/10): sbalzato via in movimento dovrebbe cadere per gravità, ma le ruote di Chaos lo tengono su (resta inclinato di 15-20°): provati attrito ridotto, ruote a sfera, spinta laterale crescente, aiuto alla stabilità spento. Finché non cade non si vede la raccolta da terra (fatta: clip, moto che si rialza, mani sulle manopole). Da verificare anche: piedi sul marciapiede nella salita, scatti di auto e moto in paese.
- **Negozi**: mancano le stanze secondarie dei prototipi (bagno, magazzino, saletta), i tavolini fuori e le insegne dei pacchetti; un negozio a cavallo di due case attaccate lascia un po' di terreno a vista.
- **Licenze delle auto scaricate**: i nomi delle texture fanno pensare a modelli presi da giochi commerciali; prima di pubblicare vanno sostituite o verificate.

## 8. Fonti e licenze

- Edifici, strade e chiese: © contributori **OpenStreetMap**, licenza ODbL (`Research/Mazzarino80/Mazzarino_OSM_*`). Va citato nei materiali distribuiti. Sono dati di oggi, non del 1980.
- Terreno: Copernicus GLO-30 (`Copernicus_GLO30_N37_E014.tif`).
- Per gli anni '80 servono le fonti datate della Regione Siciliana (SITR):
  - riprese aeree 1977-79 e 1988-89;
  - Carta tecnica regionale (foglio 638070 "Mazzarino");
  - modello del terreno a 2 m (rilievo 2012-13).
- Risorse 3D: progetto Comune, Megascans, Megapack, Game Animation Sample (Epic). Musica e marchi protetti non vanno usati.
