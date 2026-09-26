# M7 Architecture — Split Heart

M7 is a downstream visual comparison over one validated M6
`ShadowTrialPair`. `pair.baseline_state` feeds the left `HeartTwinInstance`;
`pair.scenario_state` feeds the right instance. The frontend uses M6 deltas for
comparison rows and never recomputes canonical physiology.

The two instances are separate React Three Fiber canvases with independent
interaction controllers and cardiac clocks. Shared geometry/code is immutable
infrastructure; selection, hover, focus, animation phase, and visual overlays
remain instance-local. Linked selection is an explicit UI operation keyed by
semantic `HeartComponentId` values.

`ComparisonClock` is the one comparison timing authority. Phase-locked mode
passes one normalized phase to both canvases while retaining their actual HR
labels. Physiologic-rate mode advances each phase using its own modeled HR.
Pause, seek, reset, and re-sync affect presentation timing only.

The split surface is opened from a valid M6 pair in the Shadow Trial panel and
can be closed without changing the underlying trial. The source origin, pair
IDs, scenario label, safety text, and PV limitations remain visible in the
comparison surface.
