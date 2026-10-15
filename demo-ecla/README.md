# ÉCLA — démo pub soda pétillant (marque fictive)

Pub verticale de 24,5 s (1080 × 1920, 30 i/s), style pop éditorial : aplats de couleurs, typographie massive, canette 3D (étiquette projetée sur un cylindre), fruits dessinés, rebonds à ressort. ÉCLA, ses parfums et ses chiffres sont **inventés**. Tout est dessiné par code.

## Transitions

| Temps | Transition |
|---|---|
| 2,05 s | Éclatement de bulles depuis la canette ouverte |
| 5,85 s | Vague de liquide framboise qui monte, avec écume et bulles |
| 9,65 s | Iris circulaire qui s'ouvre depuis la canette, avec un anneau blanc |
| 13,55 s | Trois volets diagonaux aux couleurs des parfums |
| 17,55 s | Zoom à travers les lettres du logo « écla » |
| 21,35 s | Montée de bulles vers l'écran de fin |

## Son

Funk-pop en do majeur à 116 BPM : marimba, basse, clap, shaker, piano électrique, pause avant la présentation des trois canettes, passage plus calme sur le plan glacé.

Bruitages : lettres qui apparaissent, chute et choc de la canette, « pssht », pétillement, bulles, vague de liquide, rebonds, glaçons, tics de texte, scintillement du logo.

## Régénérer

```bash
pip install numpy pillow scipy
npm pack @fontsource/jost@5 && tar xzf fontsource-jost-*.tgz && mv package fontsource-jost-5.3.0
python3 ecla.py . ecla-soda-24s.mp4
```
