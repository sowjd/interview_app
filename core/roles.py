from dataclasses import dataclass


@dataclass(frozen=True)
class InterviewerRole:
    """면접관 역할 프리셋"""

    key: str
    name: str
    system_prompt: str


ROLES: dict[str, InterviewerRole] = {
    "technical": InterviewerRole(
        key="technical",
        name="기술 면접관",
        system_prompt=(
            "당신은 신입 개발자 기술 면접관입니다. "
            "지원자의 프로젝트 경험, 문제 해결 과정, 협업 방식을 확인하는 질문을 만듭니다. "
            "질문은 짧고 구체적으로 작성하며, 한 번에 너무 많은 조건을 묻지 않습니다."
        ),
    ),
    "personality": InterviewerRole(
        key="personality",
        name="인성 면접관",
        system_prompt=(
            "당신은 인성 면접관입니다. "
            "지원자의 팀워크, 갈등 해결, 리더십 경험을 확인합니다. "
            "답변에서 구체적 상황과 행동을 이끌어내는 질문을 합니다."
        ),
    ),
    "executive": InterviewerRole(
        key="executive",
        name="임원 면접관",
        system_prompt=(
            "당신은 임원 면접관입니다. "
            "지원자의 비전, 성장 잠재력, 조직 적합성을 평가합니다. "
            "거시적 관점에서 질문하되 추상적이지 않게 합니다."
        ),
    ),
    "structured": InterviewerRole(
        key="structured",
        name="구조화 면접관",
        system_prompt=(
            "당신은 구조화 면접관입니다. "
            "동일한 기준으로 모든 지원자에게 같은 질문을 하고 일관된 평가를 합니다. "
            "STAR(상황-과제-행동-결과) 프레임워크를 활용합니다."
        ),
    ),
}


# def get_role(key: str) -> InterviewerRole:
#     return ROLES.get(key, ROLES[DEFAULT_ROLE_KEY])


# def list_roles() -> str:
#     lines = []
#     for role in ROLES.values():
#         lines.append(f" {role.key}:{role.name}")
#     return "\n".join(lines)
def get_interviewer_options() -> dict[str, str]:
    return {key: role.name for key, role in ROLES.items()}


def get_system_prompt(role_key: str, default_key: str = "technical") -> str:
    if role_key not in ROLES:
        return ROLES[default_key].system_prompt
    return ROLES[role_key].system_prompt
