from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from agents.vitalguard.config import MODEL_NAME
from agents.vitalguard.prompts import (
    COORDINATOR_INSTRUCTION,
    protocol_instruction,
    trend_instruction,
)
from tools.monitor_tools import (
    analyze_current_window,
    get_latest_data,
    get_parameter_summary,
    list_scenarios,
    load_scenario,
    load_vitaldb_csv,
    set_monitor_minute,
)


coordinator_agent = LlmAgent(
    name="vitalguard_coordinator",
    description="Loads a scenario, advances the monitor stream, and prepares the downstream handoff.",
    model=MODEL_NAME,
    instruction=COORDINATOR_INSTRUCTION,
    tools=[
        FunctionTool(list_scenarios),
        FunctionTool(load_scenario),
        FunctionTool(load_vitaldb_csv),
        FunctionTool(set_monitor_minute),
        FunctionTool(get_latest_data),
        FunctionTool(get_parameter_summary),
    ],
    output_key="monitor_context",
)

trend_analyzer_agent = LlmAgent(
    name="trend_analyzer",
    description="Computes early-warning metrics and multi-parameter deterioration patterns.",
    model=MODEL_NAME,
    instruction=trend_instruction,
    tools=[FunctionTool(analyze_current_window)],
    output_key="trend_assessment",
)

protocol_recommender_agent = LlmAgent(
    name="protocol_recommender",
    description="Maps deterioration findings into prioritized escalation guidance.",
    model=MODEL_NAME,
    instruction=protocol_instruction,
    output_key="clinical_recommendation",
)

root_agent = SequentialAgent(
    name="vitalguard",
    description="A multi-agent patient-monitoring swarm that detects subtle deterioration patterns.",
    sub_agents=[coordinator_agent, trend_analyzer_agent, protocol_recommender_agent],
)
