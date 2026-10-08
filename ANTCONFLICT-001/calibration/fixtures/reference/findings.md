# ANTCONFLICT-001: ANT conflict activation in dorsal ACC (ds001907)

## The result at face value
24 healthy older adults (ds001907, session 1, runs 1-2). Behaviourally the
flanker conflict effect is large: incongruent targets are 142 ms slower than congruent
ones (t(23) = 10.27, p < 0.001); accuracy 0.986 vs 0.972.

In the dorsal-ACC sphere (MNI 0, 16, 42; 10 mm) the incongruent - congruent contrast is positive
but weak, and significant only with impulse targets: 2 s targets with error trials modelled separately t(23) = 1.82, p = 0.081;
all trials t(23) = 2.01, p = 0.057; impulse targets t(23) = 2.95, p = 0.007. The same pipeline detects
the task response clearly elsewhere (all targets vs baseline, occipital pole:
t(23) = 5.53, p < 0.001).

## The check the result needs: time on task
Incongruent trials last about 142 ms longer, and a fixed-length target regressor cannot
tell a conflict signal from a longer response (Grinband et al. 2011). The dACC ROI scales with
trial RT (RT modulator slope, per second of RT: t(23) = 5.47, p < 0.001). I refit the same contrast with time on
task in the model, in two ways:
- Targets as RT-length epochs: t(23) = 1.04, p = 0.310. The estimate is smaller and not
  significant. This model assumes the response grows with time on task, so a null here is not
  by itself evidence that there is no conflict signal.
- 2 s targets plus an RT modulator (RT mean-centred across both conditions, so the condition
  difference is estimated at matched RT): t(23) = -2.71, p = 0.013. The sign reverses: at matched RT
  the dACC response is lower on incongruent than on congruent trials. A response that only
  scaled with RT would give a difference near zero here, so the reversal is not explained by
  time on task alone and is not resolved by this analysis.

## Conclusion
At face value the dACC conflict activation of Fan et al. (2005) is weak and depends on the target
model. The positive incongruent - congruent difference is sensitive to how RT is modelled: once
time on task is in the model it is no longer significant (RT-length epochs) or reverses
(RT modulator), while the region tracks RT strongly. On these data the dACC conflict effect
therefore cannot be separated from time on task, and it does not establish a conflict-specific
dACC response. This is not evidence that a conflict signal is absent, and it does not adjudicate
the conflict-monitoring account, under which dACC activity is expected to scale with RT.
