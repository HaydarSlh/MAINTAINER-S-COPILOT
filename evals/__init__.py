# Eval harness: two golden sets, two CI gates. Writes eval_report.json every
# run (-> MinIO), diffs against the previous green build, fails CI on
# regression below eval_thresholds.yaml. "The evals are the grade."
