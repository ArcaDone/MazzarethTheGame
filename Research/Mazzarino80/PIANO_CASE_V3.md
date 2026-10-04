# Piano case V3 — "vissuto" alla RDR2

Richiesta dell'utente del 2 ottobre 2026 (foto reali di Mazzarino in chat): più piante sui muri, terrazzi e cortili interni, più antenne e grovigli di fili, meno ripetizione delle texture, negozi e bar sui lati scelti dall'utente, finestre e vetrine con stanze in parallasse (vedi `Content/Esercitazioni/ParallaxRoom`: RoomMakerBP cattura la stanza in una cubemap, cotta e usata nel materiale `Interior` della mesh `Window`). Si possono migrare risorse dal progetto `D:\UE5Projects\Comune`.

**Regole di lavoro:** un passo alla volta, ogni passo termina con un commit e con lo stato aggiornato qui sotto. Verifica sulla mappa `Houses/Maps/L_M80_Houses18_V2` (catture in `Saved/Mazzarino80/HousesV2`), poi su `L_M80_Paese`. Automazione: `Scripts/run_editor_script.ps1` + `Scripts/m80_seq.py`. Non salvare mai mappe diverse da quelle di lavoro (vedi `Scripts/m80_houses_v2_setup.py`, controllo della mappa aperta).

Legenda: `[ ]` da fare · `[~]` in corso · `[x]` fatto (con commit)

## 1. Inventario risorse
- [x] 1.1 Elenco cartelle utili in `D:\UE5Projects\Comune\Content` e nel progetto (piante, edera, capperi, mobili, insegne, lampioni, oggetti da negozio/bar, panni, vasi, cisterne) → `Research/Mazzarino80/INVENTARIO_RISORSE_V3.md`

## 2. Muri senza ripetizione e più sporchi
- [x] 2.1 Master material: hex tiling (anti-ripetizione) sulle texture base e sotto-strato
- [x] 2.2 Macchie a due scale + offset texture per casa (UV1)
- [x] 2.3 Colature sotto davanzali/balconi e cornicioni (maschera nel materiale da colore di vertice o decal)
- [x] 2.4 Verifica catture + commit — il timeout era il materiale che non compilava (campionatori ORD "Linear Color" invece di "Masks"): corretto.

## 3. Piante
- [x] 3.1 Generatore: punti di ancoraggio vegetazione (base muri, spigoli, sotto balconi, cime muri in comune)
- [x] 3.2 Stile: liste mesh vegetazione (edera, capperi, erbacce, fico d'India) + istanze nell'attore
- [x] 3.3 Muschio nel materiale (superfici alte/in ombra)
- [x] 3.4 Verifica + commit

## 4. Antenne, fili, lampioni
- [x] 4.1 4-5 tipi di antenna, più antenne per tetto
- [x] 4.2 Fasci di cavi sotto cornicioni, scatole di derivazione, lampioni a braccio
- [x] 4.3 Attore di quartiere `AM80StreetWires`: cavi che attraversano la strada tra case vicine
- [x] 4.4 Verifica + commit

## 5. Volumi: terrazzi, cortili, sopraelevazioni, scale
- [x] 5.1 Ultimo piano arretrato con terrazzo abitabile (ringhiera, vasi, stendini, cisterna)
- [x] 5.2 Cortile interno nei lotti profondi + portale ad arco con cancellata / muretto con cancello
- [x] 5.3 Sopraelevazione in mattoni forati non finita (materiale + geometria)
- [x] 5.4 Scala esterna
- [x] 5.5 Verifica + commit

## 6. Negozi e bar
- [x] 6.1 Parametro per lato "Uso piano terra": abitazione / negozi / bar
- [x] 6.2 Vetrine larghe, saracinesche (anche mezze abbassate), insegne, tende parasole
- [x] 6.3 Verifica + commit

## 7. Stanze in parallasse
- [x] 7.1 Script che costruisce N scene (cucina, camera, soggiorno, negozi, bar, deposito) con mobili migrati
- [x] 7.2 Cattura cubemap e cottura (come RoomMakerBP) → TextureCubeArray
- [x] 7.3 Materiale vetro con interior mapping e stanza scelta per finestra; UV 0-1 per vetro nel generatore
- [x] 7.4 Vetrine/bar usano le stanze negozio; alcune finestre buie o con tenda
- [x] 7.5 Verifica + commit

## Richiesta del 2 ottobre 2026 (notte): seconda tornata
Foto dell'utente: tenda di legno a listarelle davanti a porte/balconi, capochiave in ferro dei tiranti (a croce, a barra, a S) ben visibili in facciata, cartelli stradali (da modellare con Blender 4.3). Interni in parallasse: oggi stirati, si vedono bene solo da vicinissimo guardando in alto o da lontano. Più dettagli di case vecchie, rovinate, abbandonate. Alla fine screenshot "da favola".

## 8. Stanze in parallasse corrette
- [x] 8.1 Interior mapping in spazio mondo (normale + orizzontale del vetro, niente tangenti), profondità stanza regolabile, scurimento verso il fondo
- [x] 8.2 Catture di prova a 3 distanze (2 m, 6 m, 15 m) davanti a una finestra al piano terra e al primo piano + commit

## 9. Rifiniture aperte
- [x] 9.1 Scrostature dell'intonaco a macchie raggruppate (non trattini ripetuti)
- [x] 9.2 Muschio a chiazze morbide (non puntini) sui tetti
- [x] 9.3 Verifica scale esterne (facciata principale ammessa) e cortili con cattura dedicata + commit

## 10. Case vecchie e rovinate
- [x] 10.1 Capochiave dei tiranti (croce, barra, S) ai piani, vicino agli spigoli
- [x] 10.2 Tenda di legno a listarelle (stuoia) davanti a portefinestre e porte, abbassata o arrotolata con la corda
- [x] 10.3 Parametro "Abbandono": finestre murate o con tavole, persiane rotte/penzolanti, vetri rotti, coppi mancanti, più erbacce
- [x] 10.4 Verifica + commit

## 11. Cartelli stradali (Blender 4.3)
- [x] 11.1 Script Blender: palo, cartelli (stop, precedenza, divieto di sosta, senso vietato, senso unico, divieto di transito), targhe toponomastiche in marmo; texture disegnate da script → FBX in `Research/Mazzarino80/Blender`
- [x] 11.2 Import in `/Game/Mazzarino80/Kit/Signs` + materiali (texture piccole)
- [x] 11.3 Script di posa: targhe con i nomi veri delle vie (OSM) sugli spigoli, cartelli agli incroci della mappa di prova + commit

## 12. Paese e foto
- [x] 12.1 Ricuocere `L_M80_Paese`
- [x] 12.2 Screenshot "da favola" (luce dorata, inquadrature curate, 2560x1440) in `Saved/Mazzarino80/Foto`

## Elementi tipici siciliani (richiesta del 3 ottobre 2026)
Lista: arabo-normanni, barocchi, liberty/ottocenteschi (il "vittoriano" siciliano) e popolari, sempre presenti nei paesi dell'entroterra.
Già nei progetti: panni stesi (`Megapack/MiddleEast/SM_clothes_A/B`), grate (`SM_Windows_grill_01/02`), bottiglie in ceramica (Megascans `Old_Ceramic_Bottle`), vaso in legno. Il resto va modellato in Blender (script in `Research/Mazzarino80/Blender`).

| Elemento | Origine | Dove nella casa | Come |
|---|---|---|---|
| Teste di moro (vasi in ceramica di Caltagirone) | araba/popolare | parapetti dei balconi, ai lati dei portoni | Blender (vaso + volto stilizzato, maiolica dipinta) |
| Pigne di Caltagirone in ceramica | barocca/popolare | pilastri dei cancelli, angoli dei terrazzi | Blender |
| Graste: vasi di terracotta con gerani e basilico | popolare | davanzali, balconi, scale | Blender (vaso) + piante esistenti |
| Quartara e bummulo (brocche in terracotta) | araba/popolare | terrazzi, accanto alle porte | Blender |
| Panaru: cesto calato con la corda dal balcone | popolare | balconi sulla strada | Blender (cesto + corda) |
| Edicola votiva (nicchia con immagine sacra in maiolica e lumino) | barocca/popolare | spigoli delle case, sopra i portoni | Blender + texture disegnata |
| Pannelli e fasce di maioliche (riggiola) | araba/barocca | sotto i balconi, numeri civici, stipiti dei bar | texture disegnate da script + materiale |
| Numeri civici in ceramica | popolare | accanto alle porte | Blender + texture con numero |
| Batacchio del portone (mano, leone, anello) e borchie | barocca/ottocento | portoni ad arco | Blender |
| Stemma nobiliare in pietra | barocca | sopra i portali dei palazzi (stile 02) | Blender |
| Balcone a petto d'oca (ringhiera bombata) | barocca | palazzi, piano nobile | generatore (geometria) |
| Mensoloni con mascheroni | barocca | sotto i balconi dei palazzi | Blender (mensola scolpita) |
| Archi a sesto acuto e bifore con colonnina | arabo-normanna | portali e finestre di case antiche | generatore (nuovo tipo d'arco) |
| Ringhiere liberty a girali e pensiline in ferro | liberty | balconi e porte delle case 1900-1930 | generatore (ferro) |
| Lanterne in ferro battuto | ottocento | accanto ai portoni | Blender |
| Doccioni in terracotta (gronde sporgenti) | popolare | bordo dei terrazzi | Blender |
| Strattu e peperoncini a seccare | popolare | terrazzi, davanzali (estate) | Blender (tavola + collane) |
| Panni stesi tra i balconi | popolare | balconi sulla strada, terrazzi | esistenti (Megapack) + fili |

## 14. Elementi tipici siciliani
- [x] 14.1 Blender: modelli (teste di moro, pigna, grasta, quartara, bummulo, panaru, edicola, numero civico, batacchio, stemma, mensolone a mascherone, lanterna, doccione, strattu) + texture dipinte da script → `M80_Sicilia.fbx`
- [x] 14.2 Import in `Kit/Sicilia` + materiali (maiolica lucida, terracotta, ferro, pietra)
- [x] 14.3 Stile: liste "Ceramiche e oggetti siciliani" per categoria; generatore: punti di posa (parapetti, ai lati dei portoni, spigoli, sotto i balconi, terrazzi, gronde)
- [x] 14.4 Generatore: balcone a petto d'oca, archi a sesto acuto e bifore, ringhiere liberty, fasce di maiolica sotto i balconi
- [x] 14.5 Panni stesi tra i balconi e sui terrazzi (mesh Megapack migrate nel Kit)
- [~] 14.6 Verifica (catture vicine) + commit — visti in `Saved/Mazzarino80/HousesV2/sicilia2`: panni stesi, edicole, peperoncini, numeri civici, bummuli e graste, finestre ad arco acuto; petto d'oca e maioliche sotto i balconi non distinguibili (balconi in ombra): da guardare in editor o con una cattura dal basso.
- Note: modelli in `Research/Mazzarino80/Blender/m80_sicilia_blender.py` (anteprima: `m80_sicilia_preview.py`), atlante da `m80_sicilia_textures.py`; import e stili con `Scripts/m80_sicilia_setup.py` (`Kit/Sicilia`, `WallPropYaw` calcolato: -180). Regole per stile in `STYLE_SETUP`. Sulla casa: "Quantita dettagli siciliani".

## 15. Edifici fatti a mano, strade dipinte, marciapiedi, asset del Comune (3 ottobre 2026)
- Mappa definitiva del paese: `L_M80_Paese` (le case restano attori modificabili, già cotte in Nanite; strade e marciapiedi sono spline modificabili). Per il gioco la stessa mappa va poi convertita a World Partition (streaming), non serve una mappa "cotta" separata.
- Catena: `powershell -ExecutionPolicy Bypass -File Scripts/m80_town_common.ps1 [-From n]` (1 zone, 2 strade, 3 oggetti Comune, 4 marciapiedi; ogni passo salva). Foto: `Scripts/m80_town_common_photos.py` → `Saved/Mazzarino80/Foto/comune_*`.
- [x] 15.1 Zone di esclusione automatiche attorno ai blueprint fatti a mano (`/Game/Migrated/...`, alberi esclusi): involucro convesso + 1,5 m, cartella `Mazzarino80/Zone_escluse` (ricreate a ogni giro; quelle disegnate a mano non si toccano). Una casa è esclusa se il centro o più di metà del perimetro cade in una zona. Spente 3 case (una sotto la Scuola Matrice).
- [x] 15.2 Strade dipinte sul landscape: layer "Strada" (`LI_M80_Strada`, non weight-blended) in `M_M80_Landscape` con Concrete_Pavers (`T_M80_Pavers_*`, 2K). Si dipinge/cancella a mano in Landscape > Paint. Le 1016 spline stradali restano come guide (niente mesh né collisione: le case le usano per il lato strada; marciapiedi e traffico le seguono). `M80_ROADS_CLEAR=0` aggiunge senza cancellare il dipinto a mano. In UE 5.5 il layer va registrato anche nei TargetLayers del landscape (`EnsureLandscapeLayer`), altrimenti si perde al ricaricamento.
- [x] 15.3 Marciapiedi: attore "Marciapiede (Mazzarino)" (`AM80Sidewalk`): spline centrale, larghezza, altezza, lato del cordolo, appoggio sul terreno; lastra = cubo con le piastrelle del materiale "Marciapiede" in coordinate mondo (`Kit/Sidewalk/M_M80_Marciapiede`), cordolo = pezzo in pietra lavica dei blueprint `marciapiede_*`. Automatici solo sulle vie larghe (primarie/secondarie/terziarie, >= 7 m) dentro l'abitato, interrotti agli incroci, nelle zone e dove toccano case; cartella `Mazzarino80/Marciapiedi` (tag M80AutoSidewalk, rifatti a ogni giro; quelli aggiunti a mano restano).
- [x] 15.4 Segnali: no entry, divieto di sosta, senso unico, divieto di transito sostituiti dai cartelli rovinati di `Migrated/Signals` (palo + targa, fronte +Y); stop e precedenza tengono la forma con ruggine (`M_M80_Sign` parametro "Rust").
- [x] 15.5 Manifesti d'epoca (`Decals_mazza`, 15) come decal sulle facciate piatte dei fronti strada, attaccati alla casa (spariscono con lei). `MI_Decal_Dirt_Manifesto` non usato (la maschera Megapack esce come un quadrato scuro).
- [x] 15.6 Palazzi neoclassici (`Migrated/Case/NeoClassic_house` + tile `NeoclassicBuilding_*`, già presenti) su lotti lunghi delle vie principali, scala 0,9: le case sotto vengono "Disattivate" (riaccese al giro successivo).
- [x] 15.7 Auto migrate dal Comune con `Tools/Migrate/m80_migrate.py` (copia con dipendenze, stessi percorsi /Game): Fiat 126, Ape, OldCar + plugin Chaos Vehicles. Tre auto parcheggiate sul Corso. Pacchetti marketplace trascinati dai blueprint (VehicleVarietyVol2, FPWeapon, FirstPerson*, ALS) ignorati da Git; `ApeDrivable.uasset` (324 MB) solo in locale/backup.
- Da fare: i blueprint delle auto usano ancora il personaggio ALS per salire/scendere (da collegare al nostro personaggio); marciapiedi su altre vie da aggiungere a mano dove servono.

## 16. Manifesti dritti, auto guidabili, livello di prova (3 ottobre 2026, sera)
- [x] 16.1 Manifesti: il decal va ruotato di 90° (roll) con larghezza/altezza scambiate in `decal_size`; corretto in `m80_town_props.py`, rifatti in `L_M80_Paese`.
- [x] 16.2 Plugin `MazzarinoVehicles`: `AM80Car` (Chaos) con controlli costruiti in codice (W/S, A/D, Spazio, mouse, C camera, R rimette in strada, gamepad), camera con ritardo e FOV in velocità, raddrizzamento automatico. Sottoclassi con i dati veri: "Fiat 126 (guidabile)" (650 kg, motore dietro, 4 marce, ~100 km/h) e "Ape Piaggio (guidabile)" (480 kg, 3 ruote, ~60 km/h, sterzo molto ridotto in velocità). Non dipendono più dal personaggio ALS; i blueprint originali del Comune restano intatti.
- [x] 16.3 Livello `Vehicles/L_M80_ProvaGuida` (`Scripts/m80_drive_test_level.py`): rettilineo 2 km, rampe 10/20/30 %, salita 12 % tra muri, slalom, cerchio 25 m, vicolo 4 m con gomito, dossi, basolato. GameMode "Prova guida": Play, Tab cambia auto, HUD con velocità/marcia/giri.
- [x] 16.4 Telemetria automatica (`Scripts/m80_drive_telemetry.py`, `M80_TEL_ONLY=Fiat|Ape`): Fiat 0-50 5,1 s, 0-80 12,2 s, max 101 km/h, frenata 72→0 in 18,6 m; Ape 0-50 9,2 s, max 61 km/h, frenata 55→0 in 12 m; curva a mezzo sterzo a ~38 km/h stabile, nessun ribaltamento.
- [x] 16.5 Ottimizzazione: LOD generati in Unreal (`Scripts/m80_cars_lods.py`): Fiat 322k→90k→52k vertici, Ape 1,74M→648k→324k. Decimazione dell'Ape in Blender provata e scartata (al 10 % texture strappate, al 35 % ancora 240 MB). L'Ape resta fuori da Git (solo locale/backup).
- In paese le auto parcheggiate sul Corso sono ora le classi guidabili (+ OldCar come oggetto fermo).
- Da fare: salire/scendere dal nostro personaggio; traffico IA sulle spline stradali (le auto accettano comandi senza controller con `SetRequiresControllerForInputs(false)`).

## 17. Giocatore stile GTA (3 ottobre 2026, notte)
- [x] 17.1 Plugin `MazzarinoGameplay`: GameMode "Mazzarino 80 (gioco)" (predefinito del progetto in `DefaultEngine.ini`; il paese lo usa anche senza override), `AM80PlayerController`, `AM80GameHUD`.
- [x] 17.2 Salire/scendere con E (gamepad Y): il personaggio cammina alla portiera del guidatore, scivola sul sedile con la posa di guida (`Player/A_M80_Seduto_Guida`, fatta in Blender con `m80_sit_pose.py` sul mannequin UEFN), camera che sfuma su quella dell'auto. Si scende sotto i 25 km/h, dal lato libero (guidatore, passeggero, dietro, davanti). Sedili e portiere per auto in `SeatOffset`/`DoorOffset` di `AM80Car`.
- [x] 17.3 HUD: radar rotondo che sfuma sul bordo (mappa `Tools/Map/m80_make_map.py` dai dati OSM, materiale `UI/M_M80_Radar`), freccia, N, barre vita e armatura; ora, lire, stelle ricercato; nome via e veicolo in basso a destra; aiuto "Premi E" in alto a sinistra. M mappa grande, P (Start) pausa con la mappa del paese.
- [x] 17.4 Personaggio `Player/BP_M80_Giocatore` (copia del MetaHuman Kellan del sample): tuta acetata viola lucida come nella foto di riferimento (V fucsia/azzurro/lime, bande su maniche e gambe, colletto fucsia, cerniera bianca; texture dipinte da `m80_tracksuit.py` sulla geometria di felpa e pantaloni, materiale `M_M80_Acetato`), occhiali da sole (`m80_sunglasses.py`, agganciati agli occhi a runtime).
- Test automatico: `Scripts/m80_play_test.py` (`M80_PLAY_CAR=Fiat|Ape`) con screenshot in `Saved/Mazzarino80/Player/Test`.
- Da fare: viso e capelli (mullet) uguali alla foto: serve un MetaHuman dell'utente (MetaHuman Creator / Mesh to MetaHuman); poi va solo sostituito viso/capelli in `BP_M80_Giocatore`.

## Da qui si riparte (notte 2-3 ottobre 2026)
- Risultato: 916 lotti cotti in 16 min, mappa da 361 MB (anteprime) a 119 MB, versionata.
- `L_M80_Paese` ha i quartieri nuovi: 801 lotti entro 300 m dal vecchio quartiere (centro 77056,11637) + lotti entro 250 m dal Corso (centro 61754,11552). Le case nuove sono in anteprima, non cotte.
- [x] 13.1 (3 ottobre, 09:54-11:10) Lanciare `powershell -ExecutionPolicy Bypass -File Scripts/m80_town_finish.ps1`: negozi automatici, targhe e cartelli, fili, cottura di tutte le case, foto (circa 1 ora e mezza; ogni passo ricarica la mappa grande).
- [x] 13.2 Guardare le foto, poi committare le mappe una volta sola: `Content/Mazzarino80/Houses/Maps/L_M80_Paese.umap` (mai versionata, controllare la dimensione rispetto alla quota LFS) e `L_M80_Houses18_V2.umap`.
- `Content/Levels/Mazzarino80_CaseStoriche_Campione.umap` risulta modificata da prima di questa sessione: non toccata, chiedere all'utente.

## Zone per edifici fatti a mano
- Attore "Zona senza case procedurali (Mazzarino)" (`AM80ExclusionZone`): perimetro a spline chiuso + "Attiva". Le case col centro dentro spariscono (mesh, collisione, piante) e tornano spegnendo, spostando o cancellando la zona ("Aggiorna case" forza il ricalcolo). Sulla singola casa: "Disattiva (sostituita da un edificio fatto a mano)".
- L'import dei quartieri (`m80_houses_district.py`) non crea lotti nuovi dentro le zone attive; negozi automatici, targhe/cartelli e fili ignorano le case escluse.
- Test: `Scripts/m80_exclusion_test.py` (non salva).

## Stato seconda tornata (2 ottobre 2026, notte)
- 8: la causa dello stiramento era la mappatura dell'intera stanza (3,6 m) nella sola finestra e la base tangente delle mesh cotte. Ora le UV del vetro sono coordinate sulla parete della stanza (`Pane`, larghezza 3,6 m, altezza del piano) e il calcolo è in spazio mondo (normale del vetro + orizzontale). Verifica: `Scripts/m80_capture_views.py` (2,5/6/15 m).
- 9.1/9.2: scrostature raggruppate da un rumore a 7 m (`DecayClusterScale`) e più fitte vicino a terra; muschio a chiazze da 3 m, meno sui coppi.
- 10: categoria "Vissuto" sulla casa: capochiave (croce, barra, S, piastra tonda), tende di legno a listarelle (giù o arrotolate con le corde), case abbandonate (finestre murate, con tavole, vetri rotti con vano buio, persiane penzolanti o mancanti, niente lampioni e vasi, più erbacce).
- 11: `Scripts/m80_streets_world.py` (OSM → mondo, errore 0 cm sui 3216 edifici) → `streets_world.json`; `Research/Mazzarino80/Blender/m80_signs_textures.py` (6 cartelli invecchiati + 320 targhe in marmo coi nomi veri) e `m80_signs_blender.py` (Blender 4.3 → `M80_Signs.fbx`); `Scripts/m80_signs_setup.py` importa in `Kit/Signs` e posa targhe e cartelli (attori con tag M80Sign, cartella "Segnaletica").
- 12: `L_M80_Paese` con negozi automatici sulle vie principali (`M80_SHOPS=auto`), fili, 78 targhe e 53 cartelli, 202 lotti ricotti; foto con `Scripts/m80_photos.py` (sole a -30°, foschia, grading caldo). Le catture SceneCapture hanno meno GI dell'editor: ombre più dure di quanto si vede nel viewport. Le case cotte coprono solo il quartiere importato (raggio 160 m).
- 9.3: [x] verificati con `M80_VIEWS_MODE=orbit` di `m80_capture_views.py` (`Saved/Mazzarino80/HousesV2/orbit`): cortili con muro di cinta e corpo posteriore visibili; scale esterne contate dallo stato della casa.
- Piante spostate in `/Game/Mazzarino80/Kit/Plants` (versionata, texture 1K JPEG) con `Scripts/m80_plants_to_kit.py`; i redirector restano nelle cartelle escluse.
- Fili tra le case: controllo "case affacciate" allentato (fino a 3 fili per casa): 22 fili nel quartiere.

## Stato al 2 ottobre 2026 (sera)
- 3: piante in `Content/Megascans` e `Content/Megapack` (cartelle escluse da Git, copiate da Comune con `migrate_list`): gli stili le referenziano, su un clone pulito mancano finché non si spostano in `/Game/Mazzarino80/Kit` (rimandato per la quota LFS). Script: `m80_houses_plants.py` (assegna e mette il flag ISM ai materiali).
- 3.3: muschio nel master (facce in alto + fascia umida, a chiazze); da rivedere: sui tetti sembra a puntini.
- 4.3: attore `AM80StreetWires` ("Fili tra le case"), piazzato con `m80_street_wires_setup.py`.
- 5.1/5.3: parametri "Volumi" (ultimo piano arretrato, piano non finito in mattoni forati, slot materiale `Brick`).
- 6: "Uso piano terra di ogni lato" (Abitazione/Negozi/Bar); demo con `m80_houses_shops_demo.py`.
- Nuovi campi in `FM80HouseParams` cambiano l'hash: all'apertura le case cotte tornano anteprima. Ricuocere `L_M80_Paese` con `m80_houses_bake.py` (M80_BAKE_MAP).
- 5.2: lotti profondi (>= 15 m, "Probabilita cortile interno") divisi in corpo anteriore e posteriore; muri del cortile con portale ad arco e cancellata (`M80BuildCourtWall`).
- Verifica 5.2/5.4 con `m80_houses_volumes_demo.py` (forza cortili e scale su 5 lotti): lo stato della casa conta cortili, scale e piani arretrati (4 cortili, 1 scala, 7 piani arretrati/non finiti); i cortili stanno sul retro e non si vedono nelle catture di strada: da guardare in editor.
- 5.4: "Probabilita scala esterna": scala in muratura lungo un muro (prima i retri) fino a una portafinestra del primo piano, con ringhiera e vasi.
- 7: `Scripts/m80_rooms_bake.py` costruisce 7 stanze in `Rooms/L_M80_RoomStudio` (cucina, camera, soggiorno, ripostiglio, alimentari, ferramenta, bar), le cattura in cubemap (`UM80EditorLibrary.CaptureRoomCube`, 256 px HDR) e le unisce in `TCA_M80_Rooms` (`MakeCubeArray`). `M_M80_GlassInterior`: interior mapping in un nodo Custom sulle UV 0-1 del vetro, stanza da colore di vertice B (case 0-0,69, negozi 0,7-0,89, bar 0,9-1), finestre buie e con tendina. Parametro `Exposure` (0,015): l'emissivo non segue l'esposizione automatica, alzarlo per la notte. M80_ROOMS_SKIP_CAPTURE=1 rifà solo materiale e stili.
- Da sistemare: scrostature dell'intonaco a trattini ripetuti (degrado), da raggruppare a macchie.

## Note per riprendere
- Ultimo stato e decisioni: questo file + `LEGGIMI_CaseProcedurali_V2.md`.
- Compilare con l'editor chiuso: `D:\UE_5.5\Engine\Build\BatchFiles\Build.bat MazzarethTheGameEditor Win64 Development -Project=...`
- Push su GitHub un commit alla volta (quota LFS ~8,8/10 GB: niente mappe grandi a ogni passo).
