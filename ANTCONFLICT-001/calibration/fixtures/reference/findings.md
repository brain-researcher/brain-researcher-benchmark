# ANTCONFLICT-001: ANT conflict activation in dorsal ACC (ds001907)

## The result at face value
24 healthy older adults (ds001907, session 1, runs 1-2). Behaviourally the
flanker conflict effect is large: incongruent targets are 142 ms slower than congruent
ones (t(23) = 10.27, p < 0.001); accuracy 0.986 vs 0.972.

In the dorsal-ACC sphere (MNI 0, 16, 42; 10 mm) the incongruent - congruent contrast is positive
but modest: 2 s targets with error trials modelled separately t(23) = 2.00, p = 0.057; all trials
t(23) = 2.19, p = 0.039; impulse targets t(23) = 3.22, p = 0.004. Taken at face value this is a weak
reproduction of Fan et al. (2005). The same pipeline detects the task response clearly elsewhere
(all targets vs baseline, occipital pole: t(23) = 5.53, p < 0.001).

## The check the result needs: time on task
Incongruent trials last about 142 ms longer, and a fixed-length target regressor cannot
tell a conflict signal from a longer response (Grinband et al. 2011). The dACC ROI scales strongly
with trial RT (RT modulator slope t(23) = 6.84, p < 0.001). When time on task is modelled, the dACC conflict
effect does not survive:
- targets modelled as RT-length epochs: t(23) = 1.34, p = 0.194, no longer significant;
- 2 s targets plus an RT modulator (RT mean-centred across conditions): t(23) = -2.61, p = 0.016,
  the incongruent - congruent difference reverses sign.

## Conclusion
The dACC conflict activation is only weakly present at face value. It is explained by time on task:
once RT is in the model the effect is no longer significant or reverses, while the region tracks
RT strongly. On these data the dACC congruency effect cannot be separated from time on task, so
it does not support a conflict-specific dACC response. These data do not adjudicate the
conflict-monitoring interpretation, under which dACC activity should scale with RT anyway. They
only show that the incongruent - congruent difference adds nothing beyond RT here.
