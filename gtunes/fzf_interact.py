import subprocess

def fzf_select(select_from, header=None):
    args = ["fzf"]
    if header is not None:
        args.append("--header")
        args.append(header)

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

    # Check if a selection was made
    if process.returncode == 0:  # fzf returns 0 if an item was selected
        return stdout.strip()

    # Another retcode indicates no tune
    return None