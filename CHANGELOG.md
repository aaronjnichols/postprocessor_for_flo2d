## Unreleased

- Fixed `OUTNQ.OUT` summary output and merged model columns to use canonical `q_max` naming instead of legacy `outflow_max_q`.
- Fixed merged model assembly so `SUPER.OUT` columns stay canonical and missing `DEPTH.OUT` now raises a clear required-file error.
- Fixed `MANNINGS_N.DAT` extraction to read FLO-2D grid/x/y/n rows correctly so merged model outputs align Manning values to the right cells.
