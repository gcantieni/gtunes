import subprocess


def fzf_select(select_from, header=None):
    """ 
    Use fzf to select from the list or dict passed.

    Args:
        select_from: a list or dict
        header: optionally promps the user with the header
    
    Returns:
        tuple of (returned_item, user_input), where user_input is what the
            user actually entered and returned_item is what was selected from
            the passed in list. either or both may be None.
    """
    args = ["fzf"]
    if header:
        args.append("--header")
        args.append(header)

    args.append("--print-query")

    # Open a subprocess for fzf
    process = subprocess.Popen(
        args, 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
    )

    # Convert dict to list if required
    if isinstance(select_from, dict):
        select_from = [ x for x in select_from ]

    # Write options to fzf's stdin
    stdout, _ = process.communicate("\n".join(select_from))

    if process.returncode == 0:  # fzf returns 0 if an item was selected
        processed_stoud = tuple(stdout.strip().split("\n"))
        if len(processed_stoud) == 1: # User input nothing
            return processed_stoud, ""
        if len(processed_stoud) != 2:
            print(f"ERROR: fzf split stdout split on newline looks like: {processed_stoud}")
        return processed_stoud[0], processed_stoud[1]
    
    # non-zero retcode means we didn't find and item.
    # stdout will just be what the user input
    return None, stdout.strip()