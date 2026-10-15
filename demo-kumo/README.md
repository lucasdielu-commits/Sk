# KUMO — pub matcha de cérémonie (marque fictive), encre japonaise

Film vertical de 26,5 s (1080 × 1920), style sumi-e, lent et zen :
- papier washi avec ses fibres ;
- coups de pinceau simulés (épaisseur selon la pression, poils, pinceau qui s'assèche en fin de trait), révélés au rythme du geste ;
- lavis de montagnes, brume, sceau rouge.

KUMO et ses mentions sont **inventés**. Tout est généré par code.

## Scènes et transitions

| Temps | Scène | Transition |
|---|---|---|
| 0–3,9 s | Une goutte d'encre tombe et s'étale, l'ensō se trace d'un geste, « Un instant. », sceau KUMO | Grand coup de pinceau sec qui révèle la scène suivante |
| 4–9 s | Montagnes au lavis, brume, soleil vermillon, oiseaux, « Au-dessus des nuages, un thé pousse à l'ombre. » | Dissolution dans la brume |
| 9,5–14,2 s | Bambous peints segment par segment, feuilles, « KUMO · Matcha cérémonial » | Goutte d'encre qui éclot, puis l'encre se lave |
| 14,5–19,6 s | Le bol se dessine, le matcha monte avec sa mousse, le fouet, la vapeur, « Fouetté. Velouté. Vert. » | Coup de pinceau |
| 20–23,2 s | Boîte de matcha peinte, bande verte KUMO, sceau, « Première récolte de printemps » | Brume |
| 23,6–26,5 s | Grand ensō, KUMO, Matcha cérémonial, « Prends le temps. », @kumo.matcha, sceau | Retour au papier |

## Son

Koto en cordes pincées (gamme hirajoshi), flûte shakuhachi avec souffle et glissés, taiko, vent.

Bruitages : goutte d'eau, pinceau sur le papier, shishi-odoshi (le « tok » du bambou), carillons, eau versée, fouet à matcha, sceau.

## Régénérer

```bash
pip install numpy pillow scipy
npm pack @fontsource/jost@5 @fontsource/cormorant-garamond@5
for f in fontsource-*.tgz; do tar xzf "$f" && mv package "${f%.tgz}"; done
python3 kumo.py . kumo-matcha-encre-26s.mp4
```
