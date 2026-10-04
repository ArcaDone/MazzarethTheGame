# Anteprima PCG per quartieri

Aprire `/Game/Levels/Mazzarino80_PCG_Quartieri_Preview` in Unreal. È una copia di lavoro della panoramica: le mappe `Mazzarino80_Panoramica` e `Mazzarino80_CaseStoriche_Campione` restano intatte.

La mappa contiene tutti i 3.216 edifici/perimetri della panoramica, organizzati in 108 settori tecnici sotto `Mazzarino80/Quartieri_PCG/Q001`–`Q108` nel World Outliner. I settori sono divisi in 36 gruppi di tre nel [manifest](pcg_district_manifest.json). Il nome “quartiere” qui indica un gruppo di lavoro, non un quartiere storico ufficiale.

Il primo gruppo è già preparato:

| Gruppo | Settore originale | Edifici | Case PCG approvate | Volumi provvisori |
| --- | --- | ---: | ---: | ---: |
| Q001 | Isolato_campione | 14 | 10 | 4 |
| Q002 | Centro_Corso/Settore_04_00 | 53 | 3 | 50 |
| Q003 | Centro_Corso/Settore_05_00 | 18 | 5 | 13 |
| Totale | | 85 | 18 | 67 |

Le 18 case PCG utilizzano gli stessi grafi di dettaglio/materiale del campione. La generazione salvata contiene 37.037 istanze, identiche al campione. I 67 edifici non pilota nei primi tre settori e i rimanenti 3.131 edifici del paese sono ancora i volumi della panoramica: non sono stati convertiti in PCG. Le 18 case originali corrispondenti sono nascoste e senza collisione per evitare doppioni.

Per isolare un settore nell'editor, espandere `Mazzarino80/Quartieri_PCG` nel World Outliner e usare l'icona dell'occhio accanto a `Q001`, `Q002` o `Q003`. Le cartelle contengono sia gli edifici PCG sia i volumi relativi. L'occhio controlla la visibilità **nell'editor**; per un comando equivalente durante Play o nel gioco serviranno Data Layers o sottolivelli.

Questa anteprima permette di valutare scala, continuità urbana, costi e leggibilità dei PCG nel contesto dell'intero paese, senza sostituire i muri esistenti con il kit di case Blender. Prima di estendere la generazione ai lotti non pilota, occorre definire e verificare regole che seguano perimetri, quote e punti di attacco, poi misurare il primo gruppo completo e avanzare di tre settori alla volta.

La [verifica della mappa](pcg_district_preview_verification.json) riporta 3.216 edifici organizzati, 18 case PCG, 37.037 istanze e nessun errore nei controlli automatici.
