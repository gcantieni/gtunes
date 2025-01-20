import subprocess

def fzf_select(select_from):
    # Open a subprocess for fzf
    process = subprocess.Popen(
        ["fzf"], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
    )

    if type(select_from) == dict:
        select_from = [ x for x in select_from ]

    # Write options to fzf's stdin
    stdout, _ = process.communicate("\n".join(select_from))

    # Check if a selection was made
    if process.returncode == 0:  # fzf returns 0 if an item was selected
        return stdout.strip()

    # Another retcode indicates no tune
    return None