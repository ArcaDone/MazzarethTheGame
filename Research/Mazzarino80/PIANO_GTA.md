# Mazzarino 80 – Piano per arrivare a un "GTA" completo

Linea guida per i prossimi step (creato il 4 ottobre 2026, aggiornato il 7 ottobre). Ogni fase ha l'obiettivo, i passi e il criterio
"fatto quando". Le fasi sono in ordine consigliato: ognuna si appoggia alle precedenti. Lo stato del
progetto, gli strumenti, gli script e il backup sono descritti nel `README.md` del progetto.

Regole che restano valide: commit atomici con push uno alla volta, solo percorsi espliciti in `git add`;
mappa ufficiale del paese `L_M80_Paese_WP` (World Partition, un file per attore: si versionano solo gli
attori cambiati, non gli HLOD), mappa d'apertura `Main` (leggera); quota LFS circa 5,7 GB su 10; ogni
funzione nuova ha il suo test automatico in PIE (`Scripts/m80_*_test.py`) con foto.

---

## 0. Stato attuale (fatto)

- Paese `L_M80_Paese_WP` (World Partition, HLOD per le viste lontane): terreno reale, tutti i lotti
  OSM con case procedurali cotte in Nanite, edifici fatti a mano, strade OSM dipinte, marciapiedi,
  cartelli, manifesti, palazzi neoclassici, 941 lampioni a muro; strumento "Isolato da riempire".
- Atmosfera: sole reale per Mazzarino, luna, nuvole, foschia, ora blu, notte con lampioni e finestre
  accese, meteo (sereno, afa, scirocco, nuvoloso); orizzonte con colline ed Etna.
- Marciapiedi a spline: aperti, ad anello (spline chiusa) o piazza riempita con cordolo.
- Edificio delle Poste Italiane con traliccio (Nanite), importato da Blender.
- Veicoli guidabili: Fiat 126, Ape, Fiat Panda, Fiat 127, Fiat Uno, Golf GTI e Vespa (sta in piedi e
  piega in curva); nessun testacoda né ribaltamento nel test di guida; livello `L_M80_ProvaGuida`.
- Pipeline Blender → Unreal per veicoli ed edifici (`m80_prepare_vehicle.py` +
  `m80_import_blender_assets.py`): pulizia, ruote, decimazione, rig, materiali, physics asset, LOD.
- Giocatore MetaHuman in tuta acetata viola e occhiali; locomozione del Game Animation Sample (GASP):
  cammina, corre, scatta, si accovaccia, scavalca.
- E: sali/scendi dall'auto (o salti giù in corsa); posa di guida.
- HUD: radar rotondo con la mappa OSM, mappa intera (M), pausa con mappa (P), orologio, soldi, stelle,
  nomi di vie e veicoli.
- Vita, armatura, stamina; danni da cadute e investimenti; morte con ragdoll, "SEI MORTO", ritorno
  all'ospedale (L. 5.000).

- Fase 1 (armi) in gran parte fatta: armi a terra da raccogliere, quattro slot (pugni, coltello, mazza,
  revolver, Beretta, lupara), mira con IK delle braccia sul mirino, rinculo, ricarica, lasciare l'arma;
  caduta e rialzata, capriola uscendo dall'auto in corsa; HUD dell'arma e mirino.
- Fase 2 (guida) in parte fatta: salute dell'auto da urti e spari, fumo, fuoco ed esplosione, fari e
  stop, suono del motore con i giri, clacson, guarda indietro, auto parcheggiate chiuse, tachimetro,
  niente testacoda in curva veloce, 7 veicoli guidabili.

Tasti attuali: WASD, mouse, Shift scatto, Ctrl cammina, C accovacciati, Spazio salto/scavalca,
E auto, M mappa, P pausa. In auto: W/S, A/D, Spazio freno a mano, C camera, R raddrizza.

---

## 1. Combattimento e armi

Obiettivo: raccogliere, usare e lasciare armi come in GTA Vice City.

1. Sistema armi in C++ (plugin `MazzarinoGameplay`): `UM80WeaponData` (DataAsset: tipo, danno,
   cadenza, caricatore, munizioni max, gittata, dispersione, suoni, mesh, posa) e `AM80WeaponPickup`
   (a terra, ruota e brilla, si raccoglie passandoci sopra).
2. Inventario a slot come GTA: pugni, arma bianca, pistola, fucile, lancio. Rotella e tasti 1-5
   cambiano arma, G lascia l'arma a terra. Le munizioni si sommano raccogliendo la stessa arma.
3. Armi del periodo, modellate in Blender come gli occhiali: coltello a serramanico, mazza da
   baseball / bastone, revolver, Beretta 92, lupara (doppietta a canne mozze), fucile da caccia.
4. Animazioni: pose e mire di ALS (pistola a una e due mani, fucile) retargettate sullo scheletro
   UEFN del sample; rinculo procedurale; aim offset sul busto. Pugni e ricarica: Lyra (scarica
   l'utente da Fab) o animazioni fatte a mano.
5. Mira: tasto destro con camera sopra la spalla e mirino; sinistro spara; lock-on sul bersaglio più
   vicino con il gamepad (come GTA).
6. Colpi: trace con danno (`ApplyDamage` → `UM80VitalsComponent`), sangue, fori sui muri (decal),
   scintille sul ferro, vetri delle auto che si rompono, rinculo della camera.
7. Corpo a corpo: combo di pugni, colpi con arma bianca; i pedoni colpiti cadono.
8. Rialzarsi: dopo un investimento o un'esplosione ragdoll breve e animazione di rialzata
   (ALS GetUp); capriola quando si salta giù dall'auto (ALS LandRoll).
9. HUD: icona dell'arma e munizioni in alto a destra, mirino, munizioni in caricatore/totali.

Fatto quando: nel paese ci sono armi a terra, le prendi, le cambi, spari a bersagli e auto, le lasci
cadere; test automatico con foto.

Stato: fatti i punti 1-3, 5 (senza lock-on da gamepad), 6 in parte (fori, vetri), 8 e 9. Restano:
fucile da caccia, lock-on, sangue e scintille, combo di pugni e corpo a corpo completo.

## 2. Guida completa

Obiettivo: auto che si guidano e si rompono come in GTA, più veicoli d'epoca.

1. Camera auto: segue meglio in curva e in retromarcia, guarda indietro (tasto), visuale dal cofano.
2. Danni: salute del veicolo, fumo bianco → nero → fuoco → esplosione (Niagara, M5VFX / Realistic
   Starter VFX già nel progetto); ammaccature semplici (pezzi staccabili: paraurti, portiere, cofano);
   gomme forate dagli spari.
3. Luci e suoni: fari e stop (notte), clacson, motore per tipo di auto, sgommate, frenate, urti.
4. Uscire dall'auto con animazione di apertura della portiera; rubare un'auto con il guidatore
   (trascinarlo fuori) e auto chiuse a chiave (finestrino rotto).
5. Nuovi veicoli anni '80 siciliani: Fiat Panda, Fiat 127, Fiat Ritmo, Alfa Giulietta, Vespa e
   motorino (Ciao), trattore, Alfetta dei Carabinieri, ambulanza, autobus AST.
6. Moto e scooter: guida su due ruote, cadute.
7. Contachilometri e nome della stazione radio nell'HUD.

Fatto quando: auto che si danneggiano ed esplodono, almeno 6 veicoli guidabili, furto d'auto
con guidatore.

Stato: fatti i punti 2 (senza pezzi staccabili e gomme forate), 3, 6 (Vespa) e 7 (tachimetro);
Panda, 127, Uno, Golf e Vespa importati. Restano: visuale dal cofano, ammaccature e pezzi
staccabili, gomme forate, apertura animata della portiera, trascinare fuori il guidatore, Ritmo,
Giulietta, Ciao, trattore, Alfetta dei Carabinieri, ambulanza, autobus AST, nome della radio.

## 3. Paese vivo

Obiettivo: pedoni e traffico che rendono Mazzarino abitato.

1. Pedoni: personaggi variati (MetaHuman e mesh più leggere per la distanza), abiti anni '80,
   anziani con la coppola, donne con la spesa, bambini; locomozione GASP; LOD e numero massimo
   per prestazioni (Mass AI o pool di attori).
2. Comportamenti: passeggiano sui marciapiedi (spline già fatte), stanno seduti davanti casa,
   chiacchierano in piazza, fuggono quando spari, reagiscono se li urti, chiamano i carabinieri.
3. Traffico AI: auto che seguono le spline delle strade, precedenze agli incroci, si fermano davanti
   ai pedoni e agli ostacoli, suonano il clacson, si parcheggiano.
4. Ciclo giorno/notte legato all'orologio dell'HUD: sole, lampioni, finestre accese, meno gente di
   notte; meteo semplice (sereno, nuvoloso, scirocco con foschia, pioggia rara).
5. Vita di paese: campane della chiesa madre, processione o mercato in certe ore, bar con tavolini.

Fatto quando: si cammina per il paese con gente e auto in movimento che reagiscono al giocatore,
senza scendere sotto i 60 fps sulla RTX 3070 Ti.

## 4. Ricercato e forze dell'ordine

Obiettivo: livello di ricercato a stelle come GTA.

1. Reati: sparare, colpire, investire, rubare auto davanti a testimoni → stelle (1-5).
2. Risposta: 1-2 stelle vigili/carabinieri a piedi, 3 stelle Alfette e posti di blocco, 4-5
   rinforzi da Caltanissetta, elicottero.
3. Fuga: perdere di vista la polizia fa calare le stelle; ripararsi in un garage o cambiare auto.
4. Arresto: "ARRESTATO", ritorno alla caserma, perdi armi e soldi (come la morte).
5. HUD: stelle che lampeggiano, radar con i lampeggianti.

Fatto quando: commettere reati porta inseguimenti credibili che si possono perdere.

## 5. HUD, menu e salvataggi

Obiettivo: interfaccia da GTA anni 2000 con identità anni '80.

1. HUD stile Vice City: orologio, soldi, vita/armatura, arma, stelle in alto a destra; radar con
   icone (missioni, negozi, ospedale, caserma, rifugio, garage, waypoint).
2. Font anni '80 a licenza libera (stile Pricedown senza usare Pricedown).
3. Messaggi: titoli delle missioni, sottotitoli dei dialoghi, notifiche "Missione compiuta".
4. Menu di pausa: mappa navigabile (zoom, spostamento, waypoint, legenda), statistiche, brevi,
   impostazioni (grafica, audio, comandi, sensibilità, sottotitoli), esci.
5. Schermata titolo e caricamento con immagini d'epoca di Mazzarino.
6. Salvataggi (`USaveGame`): nel rifugio, con soldi, armi, missioni completate, auto in garage,
   statistiche, ora del giorno.

Fatto quando: si inizia da un menu, si salva e si ricarica la partita, l'HUD è completo.

## 6. Economia e luoghi

1. Soldi: trovati, guadagnati con le missioni, spesi in negozi e spese ospedale/caserma.
2. Negozi: armeria/caccia e pesca, ferramenta, bar (cibo = vita), tabacchi, carrozzeria (ripara e
   ridipinge l'auto, toglie le stelle), garage del rifugio.
3. Telefoni pubblici SIP a gettoni per le missioni, edicola con giornali che commentano le missioni.
4. Interni selezionati (bar, chiesa, rifugio, caserma, ospedale) con caricamento senza stacchi.

## 7. Missioni e storia

1. Sistema missioni in C++: missione = sequenza di obiettivi (vai a, entra in auto, segui,
   elimina, consegna, sopravvivi) con checkpoint, fallimento e ricompensa; avvio da marcatore sulla
   mappa o da telefono.
2. Scene d'intermezzo con Sequencer e dialoghi in siciliano con sottotitoli in italiano.
3. Storia ambientata nella Mazzarino del 1980-89: personaggi, catene di missioni per committenti
   diversi, finale.
4. Attività secondarie: consegne con l'Ape, taxi, ambulanza, corse in motorino, gare di auto
   sulle strade di campagna.
5. Collezionabili (santini, gettoni) e statistiche di completamento.

## 8. Audio e radio

1. Suoni: passi per superficie, armi, motori, ambiente (campane, cani, galline, voci in piazza,
   cicale d'estate).
2. Radio in auto con stazioni locali anni '80: musica originale o royalty-free (niente brani protetti
   da copyright), DJ e pubblicità finte.
3. Voci dei pedoni in siciliano (frasi brevi) e doppiaggio dei personaggi delle missioni.

## 9. Mondo più grande

1. Estendere case e dettagli a tutto il paese (PIANO_CASE_V3.md).
2. Campagna intorno: strade provinciali, uliveti, campi di grano, masserie, cave.
3. Altri luoghi raggiungibili in auto (frazioni, lago, paesi vicini in versione ridotta).
4. Prestazioni: World Partition con streaming, HLOD, Nanite per le case, LOD per auto e pedoni.

## 10. Tecnica e rilascio

1. Comandi completi da gamepad e rimappabili.
2. Opzioni grafiche e scala di risoluzione (TSR/DLSS).
3. Build impacchettata Windows (Shipping) e test di avvio fuori dall'editor.
4. Test automatici per ogni sistema (play test in PIE con report JSON e foto), da lanciare prima
   di ogni commit importante.
5. Gestione LFS: tenere fuori dal repo i file rigenerabili, valutare un piano LFS più grande prima
   di aggiungere audio e animazioni in quantità.

---

## Ordine consigliato e traguardi

| Traguardo | Fasi | Risultato giocabile |
|---|---|---|
| A – "Sandbox" | 1, 2 (punti 1-4) | Armi, auto che si rompono, furto d'auto |
| B – "Paese vivo" | 3, 4 | Pedoni, traffico, carabinieri e stelle |
| C – "Gioco" | 5, 6 | Menu, salvataggi, soldi e negozi |
| D – "Storia" | 7, 8 | Prime missioni con dialoghi e radio |
| E – "Mondo" | 9, 10 | Campagna, build impacchettata |

Prossimo passo concreto: chiudere i punti aperti tecnici qui sotto, poi completare la fase 2 (furto
d'auto con il guidatore, portiere, danni visibili) per chiudere il traguardo A e passare alla fase 3.

---

## Punti aperti (tecnici, fuori dalla direzione di gioco)

Fatti il 6 ottobre: bake di tutto il paese e conversione a World Partition (`L_M80_Paese_WP`, la
vecchia `L_M80_Paese` è stata cancellata), HLOD, Nanite sui dettagli, lampioni.

1. Macchia nel cielo nelle viste aeree molto alte (difetto delle nuvole, non dell'orizzonte).
2. Mappe `DefaultLevel` e `PaintLandscapeMaterial`: risultavano modificate da una sessione
   dell'editor e sono entrate così nel commit del 4 ottobre; controllare che vadano bene.
3. `.git_old` (38 GB, fuori da git) contiene la vecchia storia di 95 commit: spostarlo su un altro
   disco o cancellarlo quando non serve più.
4. Poste: alcune lamelle della facciata sono storte come nel modello originale; sistemarle in Blender,
   poi reimportare con la pipeline.
5. Zona delle Salesiane da riempire con "Isolato da riempire"; candelabri a tre luci da piazzare
   nelle piazze.
