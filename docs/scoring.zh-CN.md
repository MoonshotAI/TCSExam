TCSExam 的计分公式、输入格式与汇总方法。
供计算各任务成绩及综合指数（Index）的研究者阅读。

<a id="score-calculation"></a>

# 分数计算

[English](scoring.md) | [简体中文](scoring.zh-CN.md)

TCSExam 报告四类题型的成绩及其加权综合指数。评测输出保留任务判分器的原始奖励。综合指数对两类证明题型采用完整证明通过与否的指标，对 Solver 题型采用固定参照下的相对分数，对构造题型采用原始奖励。

<a id="the-four-track-scores"></a>

## 四类题型的成绩

读法说明：每行给出应填入尝试记录表的数值。

| 题型 | 综合指数使用的数值 | 范围 |
|---|---|---|
| 定理证明 | 判分器接受完整证明：1；其余情况：0 | 0–1 |
| Solver 工程 | 将各实例结果与固定参照 `paper-k3-fixed-260925` 比较，参照值见 [Full](../src/tcsexam/references/paper-k3-fixed-260925-full.json) 和 [Lite](../src/tcsexam/references/paper-k3-fixed-260925-lite.json) JSON 文件 | 0–1 |
| 构造 | 任务的原始奖励，包括超过参照值时的额外得分 | 非负；可超过 1 |
| 开放猜想 | 完整证明或证伪被接受：1；其余情况：0 | 0–1 |

固定参照包含冻结后的 K3 实例结果，用于定义 Solver 的相对分数。评测其他模型时，参照的版本与数值保持固定。Lite 包含 Full 中对应的五道任务。

判分器的原始输出可能包含定理证明的部分得分，或开放猜想的中间结果。除非判分器接受了完整证明或完整解决结果，否则将这些数值转换为 0。构造任务的公式保持不变。

综合指数为 `30P + 30S + 30C + 10O`，其中各字母依次代表定理证明、Solver、构造和开放猜想题型的平均分。指标标识符为 `tcsexam-index-original-30303010-v0.1`。综合指数以点为单位，报告时应同时报告四类题型的平均分。由于构造任务奖励可以超过 1，综合指数可以超过 100。

<a id="average-in-this-order"></a>

## 按以下顺序求平均

1. 对每道任务被采用的重复尝试求平均。
2. 在每个题型内，对各任务平均分等权求平均。
3. 将各题型平均分分别乘以 30、30、30 和 10，再相加。

重复三次的任务与重复一次的任务，在题型内具有相同权重。缺少任务结果或计划中的重复尝试时，结果标为不完整，综合指数为 null。题型权重保持固定。若其他部分完整，但包含暂定采用的尝试，则结果标为暂定。Full 和 Lite 分别报告，每套任务中的在线与离线 Solver 协议也分别报告。

<a id="fixed-reference-solver-calculation"></a>

## 固定参照下的 Solver 计分

对于每个参照实例，令 `mu` 为其固定参照值的平均值，`s` 为这些值的样本标准差。设 `scale = max(s, 0.02 * abs(mu), 1e-9)`。对于有效的候选值 `A`：

- 最大化：`z = (A - mu) / scale`；
- 最小化：`z = (mu - A) / scale`；
- 实例分数：`Phi(z)`，即标准正态分布的累积分布函数。

对符合计分条件的实例分数求平均，得到任务分数。有效值等于 `mu` 时得 0.5 分。求解器提交无效解、超时或崩溃时，该实例得 0 分。缺失结果和基础设施故障属于不完整观测，需要修复判分输入后再计分。

Full 参照包含 1,860 个符合计分条件的实例；另有 32 个实例的可用参照结果不足两个，列于 `unscored_reference_instances`。这些实例的观测结果仍应保留在结果记录中。计分程序将不在计分集合中的记录报告为 `unscored_instances`，并在求平均时排除。这一固定参照指标与原始判分奖励中使用基线和已知最好值作为分母的指标相互独立。

每道参照任务用 `kind: "objective"` 表示目标值，或用 `kind: "solve"` 表示求解成功指标，同时声明优化方向和参照值。对于 `solve`，同一公式使用 1 表示已解出，0 表示未解出。每个参照实例至少需要两个可用值。自定义参照必须提供这些字段及两个尺度下限；参照发生变化时，应另设版本。

<a id="from-instance-records-to-a-task-score"></a>

## 从实例记录计算任务分数

将终判的各实例结果保存为 JSON 列表。目标值记录使用 `instance`、`status` 和 `A`；求解率记录可以用布尔值 `solved` 代替 `A`。只有有效且已评估的结果才使用 `status: "ok"`。已经完成的求解器失败应使用对应的失败状态，如 `timeout`、`invalid` 或 `certificate_failed`。

例如，两个实例的最大化计算可以使用以下记录：

```json
[
  {"instance": "example-1", "status": "ok", "A": 12},
  {"instance": "example-2", "status": "timeout"}
]
```

若第一个实例的参照值为 `[10, 12, 14]`，则其 `mu` 为 12，`scale` 为 2，得分为 0.5。超时实例得 0 分，因此任务平均分为 0.25。这些名称和数值仅用于说明公式。实际评测时，使用任务完整的终判记录和所选的固定参照：

```bash
tcsexam solver-score --task maxcut-mqlib \
  --records my-final-instance-records.json --reference lite \
  --output build/maxcut-relative.json
```

输出包含 `relative_score`、各实例分数、未计分实例名称和 `reference_id`。将 `relative_score` 填入尝试记录表，同时保留原始判分奖励和实例记录。如果缺少应计分的实例、实例名称重复或出现基础设施状态，程序会报错。

<a id="attempt-table"></a>

## 尝试记录表

每次尝试在 CSV 中占一行，包含以下列：

```csv
model,track,item,attempt,score,adoption_status,score_status,score_type,solver_protocol
my-model,solver,maxcut-mqlib,1,0.25,selected,valid,fixed_reference_relative,offline
```

上面的分数用于说明行格式。请填入该任务该次尝试实际计算出的 `relative_score`。计算综合指数前，补齐其余选中任务及计划中的重复尝试。

读法说明：逐字段查看表格。合法的零分属于有效观测分数。

| 字段 | 取值与含义 |
|---|---|
| `adoption_status` | `selected` 表示采用该次尝试；`selected_provisional` 表示暂定采用；`excluded` 表示保留该次尝试，但不纳入汇总。 |
| `score_status` | `valid` 包括合法的零分。`judge_failed`、`not_finished` 和 `missing` 等状态表示计划结果尚不完整。 |
| `score_type` | Solver 必须使用 `fixed_reference_relative`。其他题型可使用 `original_task_score`，其中定理证明和开放猜想的分数须已转换为 0 或 1。 |
| `solver_protocol` | Solver 行声明 `online` 或 `offline`；其他题型可留空。 |
| `attempt` | 在每个模型、题型和任务内唯一的标识符。 |

汇总前声明计划重复次数和采用规则。如果替换某次尝试，将原行保留为 `excluded`，并记录采用替代结果的原因。汇总程序会拒绝重复标识和超过计划数量的已采用重复尝试。

<a id="recalculate-an-index"></a>

## 重新计算综合指数

创建 `cohort.json`，声明任务套件、Solver 协议、固定参照以及每道任务计划采用的重复次数：

```json
{
  "suite": "lite",
  "solver_protocol": "offline",
  "solver_reference_id": "paper-k3-fixed-260925",
  "models": {"my-model": {"attempts_per_task": 1}}
}
```

准备包含全部二十道 Lite 任务的 `attempts.csv`，然后运行：

```bash
tcsexam score --suite lite --attempts attempts.csv --cohort cohort.json \
  --output build/index.json
```

所有被采用的 Solver 行必须与 cohort 中的协议一致，并使用声明的参照。保留 `solver-score` 输出，以说明这些分数由哪个参照产生。汇总程序读取尝试记录表中的任务分数与标签；应在这些分数之外一并保留实例记录。

例如，若最终题型平均分为 `P=0.4`、`S=0.25`、`C=1.2` 和 `O=0`，则综合指数为 `30×0.4 + 30×0.25 + 30×1.2 + 10×0 = 55.5` 点。若缺少一道计划任务的结果，输出会改为 `status: "incomplete"` 和 `index: null`，并通过覆盖情况和问题列表指出缺失结果。
