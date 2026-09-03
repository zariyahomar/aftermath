from langchain_core.prompts import ChatPromptTemplate

from aftermath.llm import get_llm
from aftermath.prompts import EXTRACT_EXAMPLES, SYSTEM_EVALUATOR, SYSTEM_EXTRACT, SYSTEM_PLANNER, SYSTEM_ROUTER
from aftermath.schemas import ExtractedObligations, PayoffPlan, PlanEvaluation, RouterOutput
import json


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

def build_extract_chain():

    example_block = json.dumps(EXTRACT_EXAMPLES, indent=2)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=SYSTEM_EXTRACT
                + "\n\nFew-shot examples:\n"
                + example_block
            ),
            ("human", "{document}"),
        ]
    )

    return prompt | get_llm(temperature=0.0).with_structured_output(
        ExtractedObligations
    )

def build_router_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_ROUTER),
            ("human", "{message}"),
        ]
    )
    return prompt | get_llm(temperature=0.0).with_structured_output(RouterOutput)


def build_planner_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PLANNER),
            (
                "human",
                "Available cash: {available_cash}\n\n"
                "Analyses JSON:\n{analyses}\n\n"
                "Risk tool output:\n{risk}\n\n"
                "Evaluator feedback (may be empty): {feedback}",
            ),
        ]
    )
    return prompt | get_llm(temperature=0.2).with_structured_output(PayoffPlan)


def build_evaluator_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_EVALUATOR),
            ("human", "Cash: {available_cash}\nAnalyses:\n{analyses}\n\nPlan:\n{plan}"),
        ]
    )
    return prompt | get_llm(temperature=0.0).with_structured_output(PlanEvaluation)
