# « Elle s'était oubliée » — film publicitaire Sorienka Studio

Format : 9:16 vertical · 1080 × 1920 · 30 i/s · version longue de 39 s et version courte de 15 s

## 0. Ce qui a été livré, et ses limites

**Fichiers livrés** dans `videos/` :

- `elle-s-etait-oubliee-39s.mp4`
- `elle-s-etait-oubliee-15s.mp4`

C'est un **montage animé de tes images fixes** : mouvements de caméra lents (zoom et recadrage progressif), étalonnage qui passe du froid au chaud, fondus, lumière chaude, grain, textes et musique originale. Ce n'est **pas encore un film tourné ou généré en vidéo**. Pour obtenir de vrais mouvements (elle soupire, pose son téléphone, retire le masque), il faut générer les plans avec les prompts du §3, ou les tourner, puis les remplacer dans le montage.

**Limites à corriger avant diffusion :**

| Problème | Pourquoi | Solution |
|---|---|---|
| Pas de voix off enregistrée | Aucun outil de synthèse vocale n'est disponible ici | Le texte de la voix off s'affiche en sous-titres, ce qui fonctionne sans le son. Enregistre la voix du §5 et pose-la dans CapCut. |
| Ce n'est pas la même femme d'une scène à l'autre | Tes images montrent des personnes différentes | Génère tous les plans avec **une seule** image de référence du personnage (fiche du §2). |
| Sachet issu de la planche IA | Le vrai packaging n'a pas encore été fourni | Remplace `c_sachet`, `c_hero` et `c_texture` par des photos réelles. |
| Images écartées | YURI et Biodance sont **d'autres marques** (interdit de les montrer dans ta pub). Le masque rigide sur marbre ne ressemble pas au produit. La scène avec cœur lumineux et chocolats fait trop Saint-Valentin, donc kitsch. La femme au masque crème ne correspond pas au produit. | Non utilisées dans le montage. |
| Bougies d'une marque tierce dans l'image du bain | Les étiquettes sont lisibles sur les bords de l'image | Retirées par le recadrage. À éviter dans les futures générations (prompt « unbranded candles »). |

---

## 1. Storyboard (version 39 s)

| # | Temps | Plan (image utilisée) | Caméra / lumière | Voix off (sous-titre) | Texte de marque |
|---|---|---|---|---|---|
| 1 | 0,0–5,6 | **Le reflet.** Une femme fatiguée devant le miroir de sa salle de bain, les mains sur les joues (image 1) | Approche lente vers le reflet. Lumière froide, désaturée, fondu depuis le noir | « À force de penser à tout le monde… / …elle avait oublié une personne. » | Heure « 21:47 » en haut à gauche, rien d'autre |
| 2 | 5,6–8,6 | **Le déclic.** Bougies et lumière du meuble de salle de bain (image 3, recadrée sans visage) | Léger recul. L'étalonnage passe du **froid au chaud** et une lumière ambrée apparaît | « Celle qui méritait aussi / un peu d'attention. » | — |
| 3 | 8,6–11,2 | **La main et le masque.** Gros plan sur des doigts qui tiennent le masque translucide | Carte produit sur fond nacré, zoom lent | — | — |
| 4 | 11,2–14,2 | **Le sachet Sorienka** | Reflet nacré qui balaie le sachet | « Parfois, il suffit de commencer / par un petit geste. » | « Sorienka Studio » |
| 5 | 14,2–16,8 | **Le packshot** sur un drap de satin, avec sa boîte | Reflet nacré, zoom lent | (suite) | (suite) |
| 6 | 16,8–20,0 | **Le rituel.** Elle lisse le masque, en peignoir rose (image 4) | Léger zoom vers le visage, lumière neutre et douce | « Quelques minutes pour ralentir. » | « Ton moment. » |
| 7 | 20,0–22,5 | Masque posé, serviette sur la tête, devant le miroir (image 6) | Zoom lent qui se réchauffe | « Respirer. » | « Ton rituel. » |
| 8 | 22,5–26,1 | Détente dans le bain, yeux fermés, tasse à la main, bougies (image 7, recadrée) | Zoom très lent, lumière chaude qui pulse | « Prendre soin de soi. » | « Toi. » |
| 9 | 26,1–32,5 | **Le nouveau regard.** Sourire devant le miroir (image 9) | Approche lente, lumière chaude, en écho au plan 1 | « Parce que prendre soin de soi / n'est pas un luxe. / C'est aussi une façon / de se retrouver. » | — |
| 10 | 32,5–39,0 | **La signature.** Logo, sachet sur fond nacré, bouton, adresse | Le fond flotte légèrement, entrée en douceur | — | SORIENKA STUDIO · « Le début de ton rituel beauté. » · « Découvre notre masque collagène. » · **DÉCOUVRIR** · sorienkastudio.myshopify.com |

**Musique** (originale, composée par synthèse, libre de droits) :

- **0 à 5,6 s :** piano seul, avec le léger souffle de la pièce.
- **À partir de 5,6 s :** une nappe douce entre.
- **À partir de 8,6 s :** des arpèges commencent.
- **16,8 s :** la musique prend de l'ampleur.
- **32,5 s :** la mélodie se résout en majeur, avec un carillon sur le logo.

## 2. Fiche de continuité (pour régénérer les plans)

**Personnage (identique dans chaque prompt) :**

```
the same woman in every shot: early 30s, light-medium warm skin with natural texture and faint freckles,
shoulder-length dark brown hair, straight brows, no makeup, oval face, soft brown eyes, small gold stud earrings
```

Génère d'abord **un portrait de référence** (visage de face, lumière neutre). Utilise-le ensuite comme référence de personnage dans chaque plan, avec la fonction de référence d'image ou de personnage de ton outil : Kling, Runway, Veo, Midjourney.

**Garde-robe :**

| Moment | Tenue |
|---|---|
| Scènes 1 et 2 | Débardeur noir, manteau beige qu'elle retire |
| Scènes 4 et 5 | Peignoir en éponge **rose poudré**, cheveux attachés en chignon bas |

**Décor :** une **seule** salle de bain, dans toutes les scènes. Miroir rectangulaire à cadre fin doré, plan de toilette en pierre beige, bougies **sans marque**, serviette crème, un fauteuil près d'une lampe chaude.

**Lumière :**

| Scènes | Lumière |
|---|---|
| 1 | Froide, 5600 K, plafonnier de face, ombres dures |
| 2 | Bascule progressive vers 3000 K (lampe et bougies) |
| 3 à 6 | Chaude et douce, contre-jour ambré, reflets nacrés |

**Étalonnage :**

- Scène 1 : désaturée, bleu-gris.
- Scènes suivantes : rose poudré, beige champagne, blanc crème.
- Jamais de rose fluo, jamais de peau lissée.

**Produit :** **uniquement les photos réelles** du sachet et du masque. Dans les générations, le sachet n'apparaît que comme une forme rose pâle sans texte, et on incruste la vraie photo au montage.

## 3. Prompts de génération vidéo (un par plan)

Ajoute à chaque prompt :

```
[personnage] · vertical 9:16 · photorealistic cinematic skincare commercial · shot on cinema camera, 50mm or 85mm lens,
shallow depth of field · natural skin texture, no retouching · subtle, believable acting · smooth slow camera ·
no text, no logo, no watermark, unbranded props
```

**1a — Retour à la maison (0–2,5 s)**

```
Night, 21:47. [personnage] enters a dim apartment entryway, drops her keys in a small ceramic dish, slips off a beige coat,
tired posture, cool blue moonlight from a window, quiet, slow handheld follow from behind.
```

**1b — Le reflet (2,5–5,5 s)**

```
Bathroom at night lit by a cold overhead light. [personnage] in a black tank top stands before a rectangular mirror,
looks at her reflection, sighs softly, lowers her eyes and stays still. Camera slowly pushes in toward the reflection.
Desaturated cool tones.
```

**2a — Le déclic (5,5–8 s)**

```
Same bathroom. She raises her eyes to the mirror, her gaze softens. She notices unbranded skincare items on the beige stone vanity,
picks up her smartphone and places it face down. The light gradually warms as she switches on a small lamp and lights a candle.
```

**2b — La main saisit le masque (8–10 s)**

```
Macro close-up: her hand reaches for a pale pink sachet (no visible text) on the stone vanity, warm candlelight, shallow focus.
```
→ Remplace ce plan par **une vraie vidéo de ta main** avec ton sachet, si possible.

**3 — La découverte (10–16 s)**
Pars de ta **photo réelle** du sachet, avec un outil image-vers-vidéo :

```
Product on a beige travertine surface, powder-pink silk drapes, pearly light reflections gliding across, slow 30-degree orbit,
the product stays perfectly unchanged.
```

**4a — Application (16–19 s)**

```
[personnage] in a powder-pink terry robe, hair tied low, gently unfolds a translucent sheet mask and smooths it onto her face
from the center outward in front of the mirror, close-ups of fingertips and mask edges, soft warm light.
```

**4b — Installation (19–22 s)**

```
She sits down in a cream armchair beside a warm table lamp, wearing the sheet mask, settles back, closes her eyes and breathes deeply.
Camera glides slowly around her in a half-orbit, soft bokeh highlights.
```

**4c — Respiration (22–25 s)**

```
Close-up on her face with the sheet mask, eyes closed, a slow deep breath visible in her shoulders, candle flicker on her skin.
```

**5a — Retrait (25–28 s)**

```
She gently peels off the sheet mask in front of the mirror, unhurried, warm light, natural skin, no visible transformation.
```

**5b — Le nouveau regard (28–32 s)**

```
Same framing as the first mirror shot but warm soft light: she looks at her reflection, relaxed, a faint genuine smile,
tucks a strand of hair behind her ear. Calm and serene, natural skin texture exactly as before.
```

**6 — La signature (32–40 s)**
Fond seul, et ta photo réelle incrustée au montage :

```
Pearly rose gradient backdrop with a pale stone pedestal at center, soft light streaks drifting slowly behind, empty space for product and logo.
```

## 4. Caméra, lumière, transitions

| Passage | Transition | Durée |
|---|---|---|
| Noir → scène 1 | Fondu depuis le noir | 0,4 s |
| 1 → 2 | Fondu enchaîné, en même temps que la bascule froid → chaud | 0,8 s |
| 2 → 3 | Fondu vers le produit, avec un balayage de lumière nacrée | 0,8 s |
| 3 → 4 | Fondu enchaîné, ou coupe sur le geste si tu as de vraies vidéos | 0,8 s |
| 4 → 5 | Fondu lent : le spectateur doit sentir le temps qui passe | 0,8 s |
| 5 → 6 | Fondu vers le fond nacré. La résolution musicale tombe sur ce fondu | 0,8 s |

**Mouvements :** uniquement lents et continus (approche, recul, demi-cercle). Pas de zoom brusque ni d'effet « glitch ».

## 5. Voix off complète

Voix féminine, proche du micro, chaleureuse, sans effet « pub ». `/` = respiration courte · `//` = pause d'environ 1 s.

| Temps | Texte | Intention |
|---|---|---|
| 0,6 | À force de penser à tout le monde… // elle avait oublié une personne. | Constat, à voix basse, presque désolée |
| 5,9 | Celle qui méritait aussi / un peu d'attention. | Douceur, début d'espoir |
| 11,6 | Parfois, / il suffit de commencer par un petit geste. | Invitation, sourire dans la voix |
| 16,9 | Quelques minutes pour ralentir. // Respirer. // Prendre soin de soi. | Lent, apaisé, on respire avec elle |
| 25,4 | Parce que prendre soin de soi n'est pas un luxe. / C'est aussi une façon // de se retrouver. | Chaleur, conviction tranquille |
| 33,0 | (optionnel) Sorienka Studio. Le début de ton rituel beauté. | Signature, posée |

## 6. Textes incrustés au montage

| Temps | Texte | Style |
|---|---|---|
| 0,4–5,0 | 21:47 | Jost Light, crème, en haut à gauche |
| 11,4–16,3 | Sorienka Studio | Cormorant, prune |
| 17,2 / 18,6 / 20,2 → 24,9 | Ton moment. · Ton rituel. · Toi. | Cormorant crème, sur une ligne, un mot après l'autre |
| 33,5 → fin | Sorienka / STUDIO | Logo (remplace-le par ton vrai fichier logo) |
| 33,5 → fin | Le début de ton rituel beauté. | Cormorant italique |
| 34,5 → fin | Découvre notre masque collagène. | Jost |
| 35,1 → fin | DÉCOUVRIR | Bouton prune, texte crème |
| 35,5 → fin | sorienkastudio.myshopify.com | Jost, petit |

Les sous-titres de la voix off sont en Jost 44, crème avec une ombre sur les plans de vie, prune sur les plans produit.

## 7. Version courte 15 s

| Temps | Plan | Texte |
|---|---|---|
| 0–3,6 | Le reflet froid (image 1) | 21:47 · « À force de penser à tout le monde… / …elle s'était oubliée. » |
| 3,6–6,4 | Sachet Sorienka avec reflet nacré | « Sorienka Studio » · « Il suffit d'un petit geste. » |
| 6,4–8,8 | Application du masque (image 4) | « Ton moment. Ton rituel. Toi. » (mot après mot) |
| 8,8–11,2 | Détente dans le bain (image 7) | (suite) |
| 11,2–15 | Signature + bouton DÉCOUVRIR + adresse | — |

## 8. Assembler les vrais plans (CapCut)

1. Projet 9:16, 1080 × 1920, 30 i/s. Importe les plans générés ou tournés dans l'ordre du §1, en coupant chacun à la durée du storyboard.
2. Mets un fondu de 0,8 s entre les scènes, mais garde des coupes franches *à l'intérieur* d'une scène (par exemple 4a → 4b).
3. Couleur : un filtre froid (température -20, saturation -30) sur la scène 1, puis une image clé qui revient à température +10 sur le plan 2a. Applique le même réglage chaud à toute la suite.
4. Voix off sur sa propre piste à -6 dB. Musique à -20 dB sous la voix et à -12 dB à la fin. Tu peux réutiliser la piste audio du MP4 livré (CapCut > Extraire l'audio).
5. Sous-titres : Légendes automatiques en français, corrigées à la main. Garde-les **au-dessus des 20 % du bas** de l'écran.
6. Textes de marque aux temps du §6. Logo : ton fichier PNG réel.
7. Bruitages discrets : clés, soupir, téléphone posé, déchirure du sachet, souffle profond.
8. Export 1080p 30 i/s, débit élevé, sans filigrane CapCut. À la publication, active l'étiquette « contenu généré par IA » si des personnes sont générées.

Pour refaire ce montage automatique avec tes nouvelles images : voir `video-source/README.md` (script `render_story.py`).
