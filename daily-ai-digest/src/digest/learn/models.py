from dataclasses import dataclass


SHEET_HEADERS = (
    "任务序号",
    "方向",
    "任务项",
    "输出",
    "状态",
    "月份",
    "优先级",
    "备注",
    "链接",
)


@dataclass(frozen=True, slots=True)
class LearningPlanCandidate:
    source_date: str
    title: str
    summary: str
    url: str
    section: str
    stars: int | None
    user_intent: str


@dataclass(frozen=True, slots=True)
class LearningPlanRow:
    task_id: str
    direction: str
    task_name: str
    output: str
    status: str
    month: str
    priority: str
    notes: str
    link: str

    def to_values(self) -> list[str]:
        return [
            self.task_id,
            self.direction,
            self.task_name,
            self.output,
            self.status,
            self.month,
            self.priority,
            self.notes,
            self.link,
        ]


@dataclass(frozen=True, slots=True)
class LearningPlanWritePlan:
    action: str
    range_name: str
    values: list[list[str]]
    message: str
    existing_task_id: str | None = None


@dataclass(frozen=True, slots=True)
class LearningPlanWriteResult:
    action: str
    task_id: str
    status: str
    message: str
