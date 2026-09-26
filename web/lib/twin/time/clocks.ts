/**
 * Compatibility entry point for temporal clocks.
 *
 * The contracts module owns the implementation so direct imports from either
 * `time` or `time/clocks` share exactly the same clock types and behavior.
 */
export {
  PlaybackClock,
  TimelineClock,
  createPlaybackClock,
  createTimelineClock,
} from "./contracts";

export type {
  PlaybackClockListener,
  PlaybackClockMode,
  PlaybackClockState,
  PlaybackClockOptions,
  TimelineClockListener,
  TimelineClockState,
} from "./contracts";
