export type CardiacPhase =
  | "atrial_systole"
  | "ventricular_filling"
  | "isovolumetric_contraction"
  | "ventricular_ejection"
  | "isovolumetric_relaxation";

export interface CardiacClockState {
  heartRateBpm: number;
  cycleDurationMs: number;
  elapsedMs: number;
  normalizedPhase: number;
  phase: CardiacPhase;
  playing: boolean;
}

export type CardiacClockListener = (state: CardiacClockState) => void;

const MIN_BPM = 20;
const MAX_BPM = 260;

function clampBpm(bpm: number): number {
  return Number.isFinite(bpm) ? Math.min(MAX_BPM, Math.max(MIN_BPM, bpm)) : 72;
}

function phaseFor(normalizedPhase: number): CardiacPhase {
  if (normalizedPhase < 0.15) return "atrial_systole";
  if (normalizedPhase < 0.42) return "ventricular_filling";
  if (normalizedPhase < 0.5) return "isovolumetric_contraction";
  if (normalizedPhase < 0.78) return "ventricular_ejection";
  return "isovolumetric_relaxation";
}

export class CardiacClock {
  private state: CardiacClockState;
  private listeners = new Set<CardiacClockListener>();

  constructor(heartRateBpm = 72) {
    const bpm = clampBpm(heartRateBpm);
    this.state = { heartRateBpm: bpm, cycleDurationMs: 60000 / bpm, elapsedMs: 0, normalizedPhase: 0, phase: phaseFor(0), playing: false };
  }

  getState(): CardiacClockState { return { ...this.state }; }

  setHeartRate(bpm: number): void {
    const heartRateBpm = clampBpm(bpm);
    if (Math.abs(heartRateBpm - this.state.heartRateBpm) < 0.01) return;
    this.state = { ...this.state, heartRateBpm, cycleDurationMs: 60000 / heartRateBpm };
    this.emit();
  }

  play(): void { if (!this.state.playing) { this.state = { ...this.state, playing: true }; this.emit(); } }
  pause(): void { if (this.state.playing) { this.state = { ...this.state, playing: false }; this.emit(); } }
  reset(): void { this.seek(0); }

  seek(normalizedPhase: number): void {
    const phase = Number.isFinite(normalizedPhase) ? normalizedPhase - Math.floor(normalizedPhase) : 0;
    this.state = { ...this.state, elapsedMs: phase * this.state.cycleDurationMs, normalizedPhase: phase, phase: phaseFor(phase) };
    this.emit();
  }

  advance(deltaMs: number): CardiacClockState {
    if (this.state.playing && Number.isFinite(deltaMs) && deltaMs > 0) {
      const elapsedMs = this.state.elapsedMs + deltaMs;
      const normalizedPhase = (elapsedMs / this.state.cycleDurationMs) % 1;
      this.state = { ...this.state, elapsedMs, normalizedPhase, phase: phaseFor(normalizedPhase) };
      this.emit();
    }
    return this.getState();
  }

  subscribe(listener: CardiacClockListener): () => void { this.listeners.add(listener); return () => this.listeners.delete(listener); }

  private emit(): void { const snapshot = this.getState(); this.listeners.forEach((listener) => listener(snapshot)); }
}

export function createCardiacClock(heartRateBpm = 72): CardiacClock { return new CardiacClock(heartRateBpm); }
