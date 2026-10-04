# Strade modificabili di Mazzarino

Mappa di lavoro: `/Game/Levels/Mazzarino80_Panoramica`.

Il 28 settembre 2026 la città è stata ribaltata globalmente sull'asse Y, come richiesto dopo il riscontro sul posto: `(X, Y, Z) → (X, −Y, Z)`. Terreno, edifici, spline e PlayerStart usano tutti il nuovo orientamento. Le quote e le larghezze non sono cambiate. Il riferimento per ulteriori importazioni è documentato in `coordinate_frame.json`; i vecchi file generati conservano il sistema precedente.

## Cosa contiene

- 1.016 spline per le strade e i percorsi presenti nell'area urbana già importata (circa 2 × 1,9 km).
- Corso Vittorio Emanuele Secondo usa la mesh `Lavica_curved` e il materiale `Material` recuperati da `Spline_StradaLavica` nel progetto Comune. Il tracciato importato è diviso in quattro attori, raccolti nella cartella `Mazzarino80/Strade_spline/Corso_Vittorio_Emanuele`.
- Le altre strade hanno una pavimentazione neutra, sostituibile per singola strada.
- Alla mesh lavica è stata aggiunta una base continua opzionale con lo stesso materiale. Entrambe le superfici seguono i punti e la larghezza della stessa spline.
- Terreno ed edifici provvisori sono stati allineati allo stesso sistema di coordinate delle spline.

Le larghezze iniziali sono indicative. Tracciati, terreno e sagome degli edifici derivano dai dati moderni descritti nel precedente stato del progetto; non costituiscono ancora una ricostruzione documentata del 1980. I 1.112 elementi del conteggio precedente includevano 96 elementi senza porzioni visibili nel ritaglio utilizzato.

## Modificare una strada

1. Nell'Outliner aprire `Mazzarino80 > Strade_spline`, oppure cercare il nome della strada.
2. Selezionare l'attore della strada. Nei dettagli, categoria **Strada**, cambiare **Larghezza (metri)** per la larghezza complessiva. Nella stessa categoria sono disponibili mesh, materiale e collisione.
3. Selezionare un punto della spline nella vista per spostarlo. Spostare il punto in Z cambia quota e pendenza. Si possono spostare anche i punti in pianta e modificare le tangenti.
4. Per cambiare larghezza soltanto in una parte della strada, modificare **Scale Y** del punto selezionato: `1` è la larghezza normale, `1,2` è il 20% in più, `0,8` il 20% in meno. La larghezza viene interpolata fra i punti.
5. Usare **Rigenera pavimentazione** se la superficie non si aggiorna dopo una modifica. Salvare la mappa.

Per creare un nuovo tratto si può duplicare una strada e modificarne i punti. Il sistema resta nel plugin locale `MazzarinoRoads`, necessario per riaprire la mappa e rigenerare le pavimentazioni.

## Cosa richiede ancora rifinitura

Il precedente effetto a triangoli era causato dalle direzioni nulle delle spline nei punti di tipo CurveClamped. La rigenerazione ora ricava una direzione stabile dai punti vicini quando la derivata è nulla. La mesh lavica originale è rettangolare: non occorre cambiarne l'orientamento per risolvere quel difetto.

Incroci, marciapiedi, piazze e scalinate richiedono modellazione dedicata. I percorsi classificati come scale sono per ora superfici continue provvisorie. Una spline permette di modificare le quote della strada; il terreno circostante può richiedere una modifica separata per raccordare i bordi.

Le collisioni sono attive, ma questo non certifica ancora la percorribilità dell'intero paese con il personaggio. Le sagome provvisorie degli edifici possono occupare parte delle strade e verranno sostituite e adattate nel passaggio successivo.

## Conservazione dei progetti

`MazzarethMap` è rimasta intatta (SHA256 verificato: `64B9F8A58710730F280A05473B72BB06E30665ADA67B067447E44D67D19A6541`). Il progetto `D:\UE5Projects\Comune` è stato letto senza modificarlo. Le risorse laviche sono state copiate in una cartella distinta, `/Game/Mazzarino80/RoadSource`.

La precedente superficie unica delle strade è conservata e disattivata nella cartella `Riferimento_strade_precedente_disattivato`.

Per la compatibilità con Unreal 5.5 è disattivata la cache di disegno delle spline (`r.SplineMesh.SceneTextures=0` in `Config/DefaultEngine.ini`): durante le prove produceva superfici collassate. I materiali delle pavimentazioni e dei volumi provvisori sono visibili da entrambi i lati. Le risorse del progetto Comune originale non sono state cambiate.

Gli script di importazione e adattamento iniziale non vanno rilanciati dopo le modifiche manuali: potrebbero sostituire le quote o i punti scelti dall'utente. Il pulsante **Rigenera pavimentazione** conserva invece i punti e i parametri impostati.
