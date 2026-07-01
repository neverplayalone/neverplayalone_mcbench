from __future__ import annotations

from npabench.evaluation.run_trace import AgentRunTrace, FinalAgentState
from npabench.missions.resource_gathering.config_schema import ResourceGatheringMissionConfig, ResourceSpec
from npabench.missions.resource_gathering.scoring import score_resource_gathering_run


def test_multi_target_scoring_uses_fixed_weights_and_max_score_100() -> None:
    mission_config = ResourceGatheringMissionConfig(
        id="resource_1_sand_dirt",
        resources=[
            ResourceSpec(
                item="logs",
                items=["oak_log", "birch_log"],
                display_name="logs",
                target_count=20,
                points=25,
                role="essential",
            ),
            ResourceSpec(
                item="cobblestone",
                items=["cobblestone"],
                display_name="cobblestone",
                target_count=20,
                points=25,
                role="essential",
            ),
            ResourceSpec(
                item="raw_meat",
                items=["beef", "porkchop"],
                display_name="raw meat",
                target_count=10,
                points=25,
                role="essential",
            ),
            ResourceSpec(
                item="sand",
                items=["sand", "red_sand"],
                display_name="sand",
                target_count=10,
                points=12.5,
                role="optional",
            ),
            ResourceSpec(
                item="dirt",
                items=["dirt"],
                display_name="dirt",
                target_count=10,
                points=12.5,
                role="optional",
            ),
        ],
    )
    trace = AgentRunTrace(
        task_id="resource_1_sand_dirt",
        agent_name="agent",
        started_at=0,
        agent_ready_at=1,
        ended_at=10,
        final_state=FinalAgentState(
            inventory={
                "logs": 20,
                "cobblestone": 10,
                "raw_meat": 5,
                "sand": 10,
                "dirt": 0,
            }
        ),
    )

    report = score_resource_gathering_run(
        mission_config,
        trace,
        final_snapshot={
            "alive": True,
            "deaths": 0,
            "distance_from_spawn": 5,
        },
    )

    assert report["max_score"] == 100
    assert report["resource_score"] == 62.5
    assert report["score"] == 62.5
    assert [resource["role"] for resource in report["resources"][:3]] == [
        "essential",
        "essential",
        "essential",
    ]
