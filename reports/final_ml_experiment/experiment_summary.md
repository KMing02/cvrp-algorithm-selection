# Final ML Experiment Summary

Rows: 1260; train: 1008; test: 252.
SBS: `MJ76-insertion/all-strain`.
Best ML model by mean regret: `RandomForest`.

## Label Distribution
- `Be83-RFCS/default`: 323 (25.6%)
- `CW64-PS/minimize-distance+2opt1`: 314 (24.9%)
- `MJ76-insertion/all-strain`: 266 (21.1%)
- `WH72-sweep/both-directions`: 238 (18.9%)
- `CMT79-2phase/default`: 119 (9.4%)

## Model Metrics
```text
             method  accuracy  balanced_accuracy  macro_f1  mean_regret  median_regret  max_regret  p90_regret  p95_regret  mean_cost_ratio  within_1_percent  within_5_percent  mean_selected_solver_runtime  median_selected_solver_runtime  train_time_seconds  predict_time_seconds
                VBS  1.000000           1.000000  1.000000     0.000000       0.000000    0.000000    0.000000    0.000000         1.000000          1.000000          1.000000                      0.358981                        0.021779            0.000000              0.000000
       RandomForest  0.400794           0.378533  0.378351     0.012404       0.002737    0.196517    0.034620    0.046539         1.012404          0.630952          0.956349                      0.462545                        0.035598            0.408109              0.042312
                KNN  0.384921           0.358766  0.353477     0.013163       0.003230    0.104478    0.037397    0.053115         1.013163          0.607143          0.944444                      0.361755                        0.034065            0.003118              0.363823
   GradientBoosting  0.345238           0.305756  0.297793     0.013690       0.005659    0.114911    0.037315    0.048991         1.013690          0.587302          0.952381                      0.394169                        0.041988            4.597622              0.005694
                SBS  0.210317           0.200000  0.069508     0.016749       0.011871    0.129927    0.038365    0.052174         1.016749          0.452381          0.944444                      0.213883                        0.095183            0.000000              0.000000
       DecisionTree  0.321429           0.287551  0.285513     0.017512       0.007146    0.387187    0.045335    0.059882         1.017512          0.551587          0.924603                      0.291707                        0.020299            0.022236              0.000732
Dummy-most-frequent  0.257937           0.200000  0.082019     0.021618       0.009944    0.184669    0.058992    0.083865         1.021618          0.500000          0.869048                      1.239699                        0.200953            0.000561              0.000227
   Dummy-stratified  0.234127           0.204250  0.205987     0.026428       0.014356    0.263274    0.070523    0.090532         1.026428          0.448413          0.837302                      0.413566                        0.032209            0.000410              0.000614
```

## Top Random Forest Features
- `capacity_pressure`: 0.0439
- `demand_std`: 0.0419
- `depot_distance_std`: 0.0408
- `depot_centrality_normalized`: 0.0402
- `total_demand`: 0.0396
- `depot_to_centroid_distance`: 0.0367
- `demand_mean`: 0.0358
- `depot_distance_mean`: 0.0342
- `demand_cv`: 0.0326
- `depot_distance_max`: 0.0318