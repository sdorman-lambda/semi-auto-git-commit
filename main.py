from halo import Halo
from openai import OpenAI
import os
import subprocess
import sys

def is_set_env_variable(env_var_name):
    """Ensure that the specified environment variable is set."""
    value = os.getenv(env_var_name)
    if value is None:
        raise EnvironmentError(f"Required environment variable '{env_var_name}' is not set.")
    return value

def is_git_repo():
    """Check if the current directory is inside a Git repository."""
    result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

def has_staged_commits():
    """Check if there are any staged commits."""
    result = subprocess.run(['git', 'diff', '--cached', '--name-only'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return bool(result.stdout.strip())

def main():

    # Create and start a spinner
    spinner = Halo(text='Processing', spinner='dots')
    spinner.start()

    # Setup client
    client = OpenAI(
      api_key=is_set_env_variable("SEMI_AUTO_API_KEY"),
      base_url=is_set_env_variable("SEMI_AUTO_API_URL"),
    )

    # The model to use
    MODEL = is_set_env_variable("SEMI_AUTO_API_MODEL")
    
    # Check that we're in a Git repo
    if not is_git_repo():
        print("You are not in a Git repository.")
        sys.exit(1)
    
    # Check that there are staged commits
    if not has_staged_commits():
        print("There are no staged commits.")
        sys.exit(1)

    # Set up the prompt
    pre_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        "You are a git commit assistant. You are to take the given output of 'git diff --cached' and provide a succinct summary of the changes for a commit message. The only output you are to provide is that summary and it should be formatted in a multi-line output in only one of two ways:\n"
        "1. If there are changes to a single file, the first line will be a summary of all changes, and each individual change will be summarized on its own line.\n"
        "2. If there are changes to multiple files, the first line will be a summary of all changes, and each individual file will be summarized on its own line.\n"
        "Reminder: Do not output anything but one of the two options above.<|eot_id|>\n"
    )

    # Get the staged commit data
    staged_commit = "<|start_header_id|>user<|end_header_id|>\n"
    staged_commit += subprocess.run(['git', 'diff', '--cached'], stdout=subprocess.PIPE, text=True).stdout
    staged_commit += "<|eot_id|>\n"

    # Combine everything into the full prompt
    post_prompt = "<|start_header_id|>assistant<|end_header_id|>"
    full_prompt = f"{pre_prompt}\n{staged_commit}\n{post_prompt}"

    # Run the model with the prompt
    response = client.completions.create(
      prompt=full_prompt,
      temperature=0,
      model=MODEL,
    )

    # We are ready to provide the commit message
    spinner.succeed('Done')

    # Commit with the generated message
    subprocess.run(['git', 'commit', '-e', '-m', response.choices[0].text])

if __name__ == "__main__":
    main()
