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
    if header is not None:
        args.append("--header")
        args.append(header)
    

    args.append("--print-query")
    
    # TODO: add --print-query and return query in different field

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
        user_input, returned_item = tuple(stdout.strip().split("\n"))
        return returned_item, user_input
    
    # non-zero retcode means we didn't find and item.
    # stdout will just be what the user input
    return None, stdout.strip()