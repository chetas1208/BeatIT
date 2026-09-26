/** Guards against applying Missing Piece responses from stale in-flight requests. */
export function shouldApplyMissingPieceResult(
  requestToken: number,
  activeToken: number,
  request: { ensembleId: string; metric: string },
  active: { ensembleId?: string; metric: string },
): boolean {
  return (
    requestToken === activeToken &&
    Boolean(active.ensembleId) &&
    request.ensembleId === active.ensembleId &&
    request.metric === active.metric
  );
}
