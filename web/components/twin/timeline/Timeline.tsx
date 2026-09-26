"use client";

import { Pause, Play, Radio, SkipBack, SkipForward } from "@phosphor-icons/react";
import { useMemo } from "react";
import type {
  TwinPlaybackRate,
  TwinPlaybackState,
  TwinSnapshot,
  TwinTimeline,
  TwinTimestamp,
} from "@/lib/twin/time/contracts";
import { TWIN_PLAYBACK_RATES } from "@/lib/twin/time/contracts";

export interface TwinTimelineProps {
  timeline: TwinTimeline | null;
  playback: TwinPlaybackState;
  onSeek: (timestamp: TwinTimestamp, snapshotId: string | null) => void;
  onPlay: () => void;
  onPause: () => void;
  onRateChange: (rate: TwinPlaybackRate) => void;
  onJumpToLive: () => void;
  onScrubStart?: () => void;
  onScrubEnd?: () => void;
  className?: string;
}

interface TimelineMarkerProps {
  snapshot: TwinSnapshot;
  position: number;
  selected: boolean;
  onSelect: () => void;
}

function formatTimestamp(timestamp: TwinTimestamp, withDate = false): string {
  return new Intl.DateTimeFormat("en", {
    timeZone: "UTC",
    month: withDate ? "short" : undefined,
    day: withDate ? "numeric" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

function formatDateRange(start: TwinTimestamp, end: TwinTimestamp): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const sameDay = startDate.toISOString().slice(0, 10) === endDate.toISOString().slice(0, 10);

  if (sameDay) {
    return `${formatTimestamp(start, true)}–${formatTimestamp(end) } UTC`;
  }

  return `${formatTimestamp(start, true)}–${formatTimestamp(end, true)} UTC`;
}

function formatQuality(snapshot: TwinSnapshot): string {
  return snapshot.quality === "synthetic" ? "synthetic replay" : snapshot.quality;
}

function snapshotForCursor(
  snapshots: readonly TwinSnapshot[],
  cursorTime: TwinTimestamp,
): TwinSnapshot | null {
  let selected: TwinSnapshot | null = null;
  const cursorMs = Date.parse(cursorTime);

  for (const snapshot of snapshots) {
    if (Date.parse(snapshot.timestamp) <= cursorMs) selected = snapshot;
    else break;
  }

  return selected ?? snapshots[0] ?? null;
}

function TimelineMarker({ snapshot, position, selected, onSelect }: TimelineMarkerProps) {
  const changedFieldCount = snapshot.changedFields.length;
  const label = `${formatTimestamp(snapshot.timestamp, true)} UTC, ${formatQuality(snapshot)}${
    changedFieldCount > 0 ? `, ${changedFieldCount} changed ${changedFieldCount === 1 ? "field" : "fields"}` : ""
  }`;

  return (
    <button
      type="button"
      className="absolute top-1/2 z-10 grid size-5 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full"
      style={{ left: `${position}%` }}
      aria-label={`Select snapshot ${label}`}
      aria-pressed={selected}
      title={label}
      onClick={onSelect}
    >
      <span
        aria-hidden
        className={`block size-2.5 rounded-full border-2 transition-[transform,background-color,border-color] ${
          selected
            ? "scale-125 border-accent-bright bg-accent-bright"
            : "border-signal bg-surface-1 hover:scale-110 hover:bg-signal"
        }`}
      />
    </button>
  );
}

function EmptyTimeline({ className }: Pick<TwinTimelineProps, "className">) {
  return (
    <section
      aria-label="Cardiac timeline"
      className={`ht-panel-raised flex min-h-28 flex-col justify-center gap-1 px-4 py-3 ${className ?? ""}`}
    >
      <p className="ht-eyebrow">Cardiac timeline</p>
      <p className="text-xs text-muted">No longitudinal snapshots are available.</p>
    </section>
  );
}

export function TwinTimelineView({
  timeline,
  playback,
  onSeek,
  onPlay,
  onPause,
  onRateChange,
  onJumpToLive,
  onScrubStart,
  onScrubEnd,
  className,
}: TwinTimelineProps) {
  const snapshots = timeline?.snapshots ?? [];
  const range = useMemo(() => {
    if (!timeline) return null;
    const startMs = Date.parse(timeline.startTime);
    const endMs = Date.parse(timeline.endTime);
    return { startMs, endMs, durationMs: Math.max(0, endMs - startMs) };
  }, [timeline]);

  if (!timeline || snapshots.length === 0 || !range) {
    return <EmptyTimeline className={className} />;
  }

  const cursorMs = Math.min(Math.max(Date.parse(playback.cursorTime), range.startMs), range.endMs);
  const sliderValue = range.durationMs === 0 ? 0 : cursorMs - range.startMs;
  const selectedSnapshot = snapshotForCursor(snapshots, playback.cursorTime);
  const hasSyntheticReplay = snapshots.some((snapshot) => snapshot.quality === "synthetic" || snapshot.provenance.some((item) => item.source === "synthetic_replay"));
  const atLive = !hasSyntheticReplay && (playback.mode === "live" || cursorMs >= range.endMs);
  const statusLabel = hasSyntheticReplay ? "REPLAY" : atLive ? "LIVE" : "REPLAY";
  const statusDescription = hasSyntheticReplay
    ? "Synthetic demo stream; latest replay state"
    : atLive ? "Latest available state" : "Historical state selected";
  const isPlaying = playback.mode === "playing";

  const seekToValue = (value: number) => {
    const nextMs = range.startMs + Math.min(Math.max(value, 0), range.durationMs);
    const nextTimestamp = new Date(nextMs).toISOString();
    const nextSnapshot = snapshotForCursor(snapshots, nextTimestamp);
    onSeek(nextTimestamp, nextSnapshot?.id ?? null);
  };

  return (
    <section
      aria-label="Cardiac timeline"
      className={`ht-panel-raised min-w-0 px-3 py-3 ${className ?? ""}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 items-center gap-2">
          <p className="ht-eyebrow">Cardiac timeline</p>
          <span
            className="ht-chip"
            data-status={atLive ? "connected" : "running"}
            title={statusDescription}
          >
            <span className={`ht-chip-dot ${atLive ? "ht-pulse" : ""}`} aria-hidden />
            <span>{statusLabel}</span>
          </span>
          <span className="truncate text-[0.68rem] text-muted">{statusDescription}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            className="ht-btn ht-btn-secondary min-h-8 px-2.5 text-xs"
            onClick={isPlaying ? onPause : onPlay}
            aria-label={isPlaying ? "Pause timeline playback" : "Play timeline playback"}
          >
            {isPlaying ? <Pause size={14} weight="bold" aria-hidden /> : <Play size={14} weight="bold" aria-hidden />}
            <span>{isPlaying ? "Pause" : "Play"}</span>
          </button>
          <button
            type="button"
            className="ht-btn ht-btn-ghost min-h-8 px-2 text-xs"
            onClick={onJumpToLive}
            disabled={atLive}
            aria-label={hasSyntheticReplay ? "Jump to latest replay state" : "Jump to latest available state"}
          >
            <Radio size={14} weight="bold" aria-hidden />
            <span>{hasSyntheticReplay ? "Latest" : "Live"}</span>
          </button>
        </div>
      </div>

      <div className="mt-3">
        <div className="relative h-8 px-2">
          <div className="pointer-events-none absolute inset-x-2 top-1/2 h-1 -translate-y-1/2 bg-line" aria-hidden="true" />
          {snapshots.map((snapshot) => {
            const position = range.durationMs === 0
              ? 0
              : ((Date.parse(snapshot.timestamp) - range.startMs) / range.durationMs) * 100;
            return (
              <TimelineMarker
                key={snapshot.id}
                snapshot={snapshot}
                position={Math.min(Math.max(position, 0), 100)}
                selected={snapshot.id === playback.selectedSnapshotId}
                onSelect={() => onSeek(snapshot.timestamp, snapshot.id)}
              />
            );
          })}
          <div
            className="pointer-events-none absolute top-1/2 z-20 h-5 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-accent-bright"
            style={{ left: `calc(${range.durationMs === 0 ? 0 : (sliderValue / range.durationMs) * 100}% + ${range.durationMs === 0 ? 8 : 0}px)` }}
            aria-hidden="true"
          />
          <input
            type="range"
            min={0}
            max={range.durationMs}
            step={1}
            value={sliderValue}
            onChange={(event) => seekToValue(Number(event.target.value))}
            onFocus={onScrubStart}
            onBlur={onScrubEnd}
            className="absolute inset-x-0 top-1/2 h-8 w-full -translate-y-1/2 cursor-pointer appearance-none bg-transparent accent-[var(--ht-accent-bright)] focus-visible:outline-2 focus-visible:outline-signal"
            aria-label="Scrub cardiac history"
            aria-valuetext={`${formatTimestamp(playback.cursorTime, true)} UTC`}
          />
        </div>

        <div className="flex items-center justify-between gap-2 text-[0.68rem] tabular-nums text-muted">
          <span>{formatTimestamp(timeline.startTime, true)} UTC</span>
          <span className="font-medium text-ink-2">
            {selectedSnapshot ? `${formatTimestamp(selectedSnapshot.timestamp, true)} · ${formatQuality(selectedSnapshot)}` : "No snapshot"}
          </span>
          <span>{formatTimestamp(timeline.endTime, true)} UTC</span>
        </div>
        <p className="sr-only" aria-live="polite">
          {statusDescription}. Cursor at {formatTimestamp(playback.cursorTime, true)} UTC.
        </p>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-2">
        <p className="text-[0.68rem] text-muted">{formatDateRange(timeline.startTime, timeline.endTime)}</p>
        <div className="flex items-center gap-1" role="group" aria-label="Playback speed">
          <SkipBack size={13} className="mr-1 text-muted" aria-hidden />
          {TWIN_PLAYBACK_RATES.map((rate) => (
            <button
              key={rate}
              type="button"
              className={`min-h-7 min-w-8 border px-1.5 text-[0.68rem] font-medium transition-colors ${
                playback.playbackRate === rate
                  ? "border-signal-line bg-signal-soft text-signal-bright"
                  : "border-transparent text-muted hover:border-line-strong hover:bg-surface-2 hover:text-ink"
              }`}
              onClick={() => onRateChange(rate)}
              aria-label={`Set playback speed to ${rate} times`}
              aria-pressed={playback.playbackRate === rate}
            >
              {rate}×
            </button>
          ))}
          <SkipForward size={13} className="ml-1 text-muted" aria-hidden />
        </div>
      </div>
    </section>
  );
}

export { TwinTimelineView as TwinTimeline, TwinTimelineView as Timeline };
