// A failed judge is not a scored zero. Keep source scores and track scales intact.
export function summarize(data, protocolId, trackId) {
  const tasks = data.tasks.filter((task) => task.track === trackId);
  const records = data.results.filter(
    (result) =>
      result.protocol === protocolId &&
      tasks.some((task) => task.id === result.task),
  );
  const modelIds = [
    ...new Set(
      data.results
        .filter((result) => result.protocol === protocolId)
        .map((result) => result.model),
    ),
  ];
  return modelIds.map((modelId) => {
    const rows = tasks.map((task) => {
      const attempts = records.filter(
        (result) => result.model === modelId && result.task === task.id,
      );
      const valid = attempts.filter((result) => result.status === "scored");
      return {
        task,
        attempts,
        valid,
        score: valid.length
          ? valid.reduce((sum, result) => sum + result.score, 0) / valid.length
          : null,
      };
    });
    const covered = rows.filter((row) => row.score !== null);
    return {
      model: data.models.find((model) => model.id === modelId),
      rows,
      covered: covered.length,
      total: tasks.length,
      valid: rows.reduce((sum, row) => sum + row.valid.length, 0),
      failed: rows.reduce(
        (sum, row) =>
          sum +
          row.attempts.filter((result) => result.status === "failed").length,
        0,
      ),
      pending: rows.reduce(
        (sum, row) =>
          sum +
          row.attempts.filter((result) => result.status === "pending").length,
        0,
      ),
      score: covered.length
        ? covered.reduce((sum, row) => sum + row.score, 0) / covered.length
        : null,
    };
  });
}
