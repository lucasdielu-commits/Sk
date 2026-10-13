# AURÈLE — film publicitaire parfum (marque fictive)

Film vertical de 26,5 s (1080 × 1920, 30 i/s), noir et or, rythme lent et cinématographique, bandes noires en haut et en bas. AURÈLE et ses notes olfactives sont **inventés**. Tout est généré par code.

## Scènes et transitions

| Temps | Scène | Transition |
|---|---|---|
| 0–3 s | Poussière d'or, un trait doré se dessine, « Il existe une heure / où tout devient or. » | Le trait s'ouvre en lumière |
| 3,5–8,2 s | Or liquide en mouvement (bruit déformé et reflets), « Nuit d'ambre » | Dissolution en fumée aux bords dorés |
| 9–14,6 s | Le flacon apparaît : d'abord le liseré, puis le verre ambré, un reflet qui balaie, le reflet au sol, « AURÈLE · Eau de parfum » | Bascule de mise au point vers la poussière du premier plan |
| 15,2–19,5 s | Trois notes dessinées au trait d'or : Ambre, Vanille noire, Bois de santal | Anneaux d'or qui s'ouvrent, puis brume de vaporisateur |
| 20–23,2 s | Le flacon sur une flaque d'or liquide, « Le soir t'appartient. » | Dissolution en fumée |
| 23,4–26,5 s | AURÈLE · PARIS · Eau de parfum 50 ml · Découvrir la collection · @aurele.paris | Fondu au noir |

## Son

Partition en ré mineur qui se résout en ré majeur à la fin : drone grave, cordes, chœur synthétique sur des voyelles, piano, grondements.

Bruitages : coulée d'or liquide, souffles de fumée, tintements de verre, plume qui trace, vaporisateur, scintillements.

## Régénérer

```bash
pip install numpy pillow scipy
npm pack @fontsource/jost@5 @fontsource/cormorant-garamond@5
for f in fontsource-*.tgz; do tar xzf "$f" && mv package "${f%.tgz}"; done
mv fontsource-jost-5.3.0* fontsource-jost-5.3.0 2>/dev/null; python3 aurele.py . aurele-parfum-26s.mp4
```
