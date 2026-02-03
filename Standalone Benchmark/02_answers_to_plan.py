from pathlib import Path
from typing import Any, Dict, List

from _common import (
    build_arg_parser,
    call_openrouter,
    ensure_run_context,
    load_json,
    parse_numbered_list,
    setup_logger,
    update_status,
    JsonStore,
    write_checkpoint,
)


def build_plan_prompt(query: str, questions: List[str], answers: Dict[str, str]) -> str:
    formatted_answers = "\n".join(
        f"Q: {question}\nA: {answers.get(question, 'Keine Antwort verfügbar')}"
        for question in questions
    )

    return (
        "Erstelle einen akademischen Deep-Research-Plan. "
        "Der Plan soll 4-7 Hauptabschnitte enthalten, mit jeweils klaren Unterpunkten, "
        "Methoden und erwarteten Outputs. Nutze die Rückfragen und Antworten.\n\n"
        f"Nutzerfrage: {query}\n\n"
        f"Rückfragen & Antworten:\n{formatted_answers}\n\n"
        "Gib den Plan als nummerierte Liste mit klaren Abschnittstiteln aus."
    )


def main() -> None:
    parser = build_arg_parser("Stage 2: Clarification answers -> Final research plan")
    parser.add_argument(
        "--answers-file",
        required=True,
        help="JSON file with clarification answers (mapping question -> answer)",
    )
    parser.add_argument(
        "--stage1-file",
        default=None,
        help="Optional path to stage1 final_output.json for query/questions",
    )
    args = parser.parse_args()

    context = ensure_run_context(args.id, Path(args.output_root), "stage2")
    logger = setup_logger(context.log_file)
    store = JsonStore(context.output_root / context.run_id / context.stage, logger)

    update_status(store, "started")
    answers_path = Path(args.answers_file)
    answers_payload = load_json(answers_path)

    stage1_path = (
        Path(args.stage1_file)
        if args.stage1_file
        else context.output_root / context.run_id / "stage1" / "final_output.json"
    )
    stage1_payload = load_json(stage1_path)

    query = stage1_payload.get("query", "")
    questions = stage1_payload.get("questions", [])
    answers = answers_payload.get("answers", answers_payload)

    store.write_named(
        "inputs.json",
        {
            "query": query,
            "questions": questions,
            "answers": answers,
            "answers_file": str(answers_path),
        },
    )
    write_checkpoint(store, {"stage": "inputs_loaded", "questions": len(questions)})

    prompt = build_plan_prompt(query, questions, answers)
    response = call_openrouter(prompt, "research_plan", store, logger)
    plan_items = parse_numbered_list(response)

    plan_payload = {
        "query": query,
        "plan_raw": response,
        "plan_items": plan_items,
        "answers": answers,
        "questions": questions,
    }

    store.write_named("plan.json", plan_payload)
    update_status(store, "completed", {"plan_items": len(plan_items)})
    logger.info("Stage 2 completed")


if __name__ == "__main__":
    main()
