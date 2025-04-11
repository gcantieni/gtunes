import argparse
from gtunes import db
import questionary

def _str_default(value):
    return value if value is not None else ""

def _get_val_from_dict(value_name, the_dict):
    """
    Args:
        value_name: the name of the value to retreive from the dictionary
        the_dict: dictionary to get value from
    Returns:
        Either the value, or None instead of falsy values. This helps with the database. 
    """
    val = the_dict[value_name]
    return val if val else None

def _edit_and_save_tune_interactively(tune: db.Tune):
    """
    Edits the input tune in-place, defaulting to the values already present in the tune.
    """
    tune_type_choices = [t.name for t in db.TuneType]
    tune_type_choices.append("")

    status_choices = [s.name for s in db.Status]
    status_choices.append("")

    responses = questionary.form(
        name = questionary.text("Name", default=_str_default(tune.name)),
        status = questionary.select("Status", choices=status_choices),
        tune_type = questionary.select("Type", choices=tune_type_choices, default=_str_default(tune.type)),
        key = questionary.text("Key", default=_str_default(tune.key)),
        comments = questionary.text("Comment", default=_str_default(tune.comments)),
    ).ask()

    tune.name = _get_val_from_dict("name", responses)
    tune.status = db.Status[_get_val_from_dict("status", responses)]
    tune.type = _get_val_from_dict("tune_type", responses)
    tune.key = _get_val_from_dict("key", responses)
    tune.comments = _get_val_from_dict("comments", responses)

    print(tune)

def tune_edit(args: argparse.Namespace) -> int:
    ret = 0

    db.open_db()

    tune, _ = db.select_tune(message="Select tune to edit")
    if not tune:
        print("Tune not found.")
        ret = 1
    else:
        _edit_and_save_tune_interactively(tune)

    db.close_db()

    return ret

def tune_add(args: argparse.Namespace) -> int:
    db.open_db()

    this_tune = db.Tune()
    # Defaults
    this_tune.status = 1

    _edit_and_save_tune_interactively(this_tune)

    db.close_db()

def tune_list(args):
    db.open_db()
    sel = db.Tune.select()
    print(f"Listing tunes.\nConditions:{"" if not args.name else " Name=" + args.name}\
{"" if not args.type else " Type=" + args.type}{"" if not args.status else " Status=" + args.status}")

    if args.name is not None:
        sel = sel.where(db.Tune.name == args.name)
    if args.type:
        sel = sel.where(db.Tune.type == args.type)
    if args.status:
        sel = sel.where(db.Tune.status == args.status)

    for tune in sel:
        print(tune)