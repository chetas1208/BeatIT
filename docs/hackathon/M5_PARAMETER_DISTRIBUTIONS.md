# M5 Parameter Distributions

The initial ensemble exposes the five bounded M4 inputs:

| Parameter | Family | Initial treatment |
|---|---|---|
| Heart rate | normal | measurement-scale spread when present |
| Preload index | normal | model proxy; EDV evidence may narrow context |
| Afterload index | normal | model proxy; blood pressure is not treated as direct afterload |
| Contractility index | normal | model proxy informed directionally by EF |
| SVR index | normal | explicit prior; no direct measurement mapping claimed |

The first implementation supports fixed, normal, lognormal, uniform, and
empirical representations. Unsupported correlations are not invented.

