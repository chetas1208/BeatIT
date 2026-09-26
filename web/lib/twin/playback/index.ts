"use client";

import { useEffect, useMemo, useSyncExternalStore } from "react";
import { PlaybackClock, TimelineClock } from "@/lib/twin/time";
import type {
  TwinPlaybackRate,
  TwinPlaybackState,
  TwinTimeline,
  TwinTimestamp,
} from "@/lib/twin/time/contracts";

export class TwinPlaybackController {
  readonly timelineClock: TimelineClock;
  readonly playbackClock: PlaybackClock;
  private snapshot: TwinPlaybackState;

  constructor(timeline: TwinTimeline) {
    this.timelineClock = new TimelineClock(timeline.startTime, timeline.endTime, timeline.endTime);
    this.playbackClock = new PlaybackClock(this.timelineClock);
    this.snapshot = this.playbackClock.getState();
  }

  getState(): TwinPlaybackState {
    return this.snapshot;
  }

  subscribe(listener: () => void): () => void {
    return this.playbackClock.subscribe(() => {
      this.snapshot = this.playbackClock.getState();
      listener();
    });
  }

  play(): void {
    if (this.timelineClock.isAtEnd() && !this.timelineClock.isAtStart()) {
      this.playbackClock.seek(this.timelineClock.getState().startTime, null);
    }
    this.playbackClock.play();
  }
  pause(): void { this.playbackClock.pause(); }
  seek(timestamp: TwinTimestamp, snapshotId: string | null): void { this.playbackClock.seek(timestamp, snapshotId); }
  beginScrub(): void { this.playbackClock.beginScrubbing(); }
  scrub(timestamp: TwinTimestamp, snapshotId: string | null): void { this.playbackClock.scrubTo(timestamp, snapshotId); }
  endScrub(): void { this.playbackClock.endScrubbing(); }
  jumpToLive(): void { this.playbackClock.jumpToLive(); }
  setRate(rate: TwinPlaybackRate): void { this.playbackClock.setPlaybackRate(rate); }
  advance(deltaMs: number): void { this.playbackClock.advance(deltaMs); }
  dispose(): void { this.playbackClock.dispose(); }
}

export function useTwinPlayback(timeline: TwinTimeline | null): {
  playback: TwinPlaybackState | null;
  controller: TwinPlaybackController | null;
} {
  const controller = useMemo(
    () => (timeline ? new TwinPlaybackController(timeline) : null),
    [timeline],
  );

  useEffect(() => () => controller?.dispose(), [controller]);
  const subscribe = (listener: () => void) => controller?.subscribe(listener) ?? (() => undefined);
  const getSnapshot = () => controller?.getState() ?? null;
  const playback = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  useEffect(() => {
    if (!controller || typeof window === "undefined") return;
    let frame = 0;
    let previous = performance.now();
    const tick = (now: number) => {
      const delta = Math.min(Math.max(now - previous, 0), 250);
      previous = now;
      controller.advance(delta);
      if (controller.getState().mode === "playing") frame = requestAnimationFrame(tick);
    };
    if (controller.getState().mode === "playing") frame = requestAnimationFrame(tick);
    const unsubscribe = controller.subscribe(() => {
      if (controller.getState().mode === "playing" && frame === 0) {
        previous = performance.now();
        frame = requestAnimationFrame(tick);
      }
      if (controller.getState().mode !== "playing" && frame !== 0) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    });
    return () => {
      unsubscribe();
      if (frame !== 0) cancelAnimationFrame(frame);
    };
  }, [controller]);

  return { playback, controller };
}
