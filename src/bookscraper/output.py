import sys
from dataclasses import dataclass
from typing import Optional

from pymongo.collection import Collection

from .book_utils import check_csv_write_permission, print_log
from .database import get_mongo_collection


@dataclass
class OutputDestinations:
    output_to_csv: bool
    output_to_mongo: bool
    can_output_to_csv: bool
    can_output_to_mongo: bool
    mongo_collection: Optional[Collection]


def resolve_output_destinations(
    requested_csv: bool, requested_mongo: bool
) -> OutputDestinations:
    """
    Runs pre-flight checks (CSV write permission, MongoDB connectivity), then either honors the
    caller's requested destinations (warning on any that turned out unavailable) or, if neither
    was requested, interactively prompts for (C)SV / (M)ongoDB / (B)oth / (E)xit.

    Exits the process if no destination is usable, or the user chooses (E)xit.
    """
    print_log("\nRunning pre-flight checks for output destinations...", "info")

    print_log("  Checking CSV write permissions...", "info")
    can_output_to_csv = check_csv_write_permission()
    if can_output_to_csv:
        print_log("  CSV write permission: OK", "info")
    else:
        print_log(
            "  CSV write permission: FAILED. CSV output will not be available.", "error"
        )

    print_log("  Checking MongoDB connection...", "info")
    mongo_collection = get_mongo_collection()
    can_output_to_mongo = mongo_collection is not None
    if can_output_to_mongo:
        print_log("  MongoDB connection: OK", "info")
    else:
        print_log(
            "  MongoDB connection: FAILED. MongoDB output will not be available.",
            "error",
        )

    if not can_output_to_csv and not can_output_to_mongo:
        print_log(
            "\nNo valid output destinations available. Please fix permission/MongoDB issues.",
            "error",
        )
        sys.exit(1)

    output_to_csv = requested_csv and can_output_to_csv
    output_to_mongo = requested_mongo and can_output_to_mongo

    if not requested_csv and not requested_mongo:
        print_log(
            "No specific output destination chosen via command line arguments (-c, -m).",
            "info",
        )
        prompt_options = []
        if can_output_to_csv:
            prompt_options.append("(C)SV")
        if can_output_to_mongo:
            prompt_options.append("(M)ongoDB")
        if can_output_to_csv and can_output_to_mongo:
            prompt_options.append("(B)oth")

        prompt_options_str = ", ".join(prompt_options)
        prompt_options_str = prompt_options_str.replace(", (B)oth", " or (B)oth")

        while True:
            if not prompt_options:
                print_log("No output options available. Exiting.", "error")
                sys.exit(1)

            choice = (
                input(f"Do you want to save to {prompt_options_str}, or (E)xit? ")
                .lower()
                .strip()
            )

            if choice == "c" and can_output_to_csv:
                output_to_csv = True
                break
            elif choice == "m" and can_output_to_mongo:
                output_to_mongo = True
                break
            elif choice == "b" and can_output_to_csv and can_output_to_mongo:
                output_to_csv = True
                output_to_mongo = True
                break
            elif choice == "e":
                print_log("Operation cancelled by user. Exiting.", "info")
                sys.exit(0)
            else:
                print_log(
                    "Invalid choice or selected option is not available. Please try again.",
                    "error",
                )
    else:
        if requested_csv and not can_output_to_csv:
            print_log(
                "CSV output requested but not available due to permission issues. Skipping CSV output.",
                "warning",
            )
        if requested_mongo and not can_output_to_mongo:
            print_log(
                "MongoDB output requested but not available due to connection issues. Skipping MongoDB output.",
                "warning",
            )

    return OutputDestinations(
        output_to_csv=output_to_csv,
        output_to_mongo=output_to_mongo,
        can_output_to_csv=can_output_to_csv,
        can_output_to_mongo=can_output_to_mongo,
        mongo_collection=mongo_collection,
    )
