import click
from github import Github
from git import Repo
from openai import OpenAI
import os
from dotenv import load_dotenv
import tempfile
from pathlib import Path


def get_config_dir():
    """Returns the appropriate config directory based on the OS."""
    if os.name == "nt":  # Windows
        config_dir = os.path.join(os.environ.get("APPDATA"), "prbot")
    else:  # Unix-like
        config_dir = os.path.join(str(Path.home()), ".config", "prbot")

    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def load_config():
    """Load configuration from the global config file."""
    config_file = os.path.join(get_config_dir(), "config")
    if os.path.exists(config_file):
        load_dotenv(config_file)


load_config()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(generate_pr)


@cli.command()
def generate_pr():
    """Generates a PR description based on the diff of the current branch using ChatGPT."""

    # Authenticate with GitHub
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        click.echo("GitHub token not found in .env file.")
        return

    g = Github(token)
    # Get current repo diff
    local_repo = Repo(".")
    branch_name = local_repo.active_branch.name
    diff = local_repo.git.diff(f"origin/main...{branch_name}")

    if not diff:
        click.echo("No changes found.")
        return

    # Use ChatGPT to generate PR description
    client = OpenAI()

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that generates PR descriptions based on git diffs.",
        },
        {
            "role": "user",
            "content": f"Please generate a concise PR description based on the git diff:\n\n {diff}",
        },
    ]

    response = client.chat.completions.create(model="gpt-4", messages=messages)

    pr_description = response.choices[0].message.content

    click.echo(f"Generated PR description:\n\n{pr_description}")

    # Push the branch to GitHub
    origin = local_repo.remote(name="origin")
    origin.push(branch_name)
    click.echo(f"Pushed branch '{branch_name}' to GitHub.")

    # Create or update PR on GitHub
    repo = g.get_repo(
        "/".join(local_repo.remotes.origin.url.split(".git")[0].split("/")[-2:])
    )

    # Check if a PR already exists
    existing_pr = None
    for pr in repo.get_pulls(state="open", head=branch_name):
        existing_pr = pr
        break

    if existing_pr:
        existing_pr.edit(body=pr_description)
        click.echo(f"Updated PR description: {existing_pr.html_url}")
    else:
        new_pr = repo.create_pull(
            title=f"PR for {branch_name}",
            body=pr_description,
            head=branch_name,
            base="main",
        )
        click.echo(f"Created PR: {new_pr.html_url}")


@cli.command()
@click.option("--api-key", prompt=True, hide_input=True, help="Your OpenAI API Key")
def setup_openai(api_key):
    """Sets up the OpenAI API key in the global config file."""
    config_file = os.path.join(get_config_dir(), "config")
    with open(config_file, "a") as f:
        f.write(f"OPENAI_API_KEY={api_key}\n")
    click.echo("OpenAI API key has been stored in global config file.")


@cli.command()
@click.option(
    "--token", prompt=True, hide_input=True, help="Your GitHub Personal Access Token"
)
def setup_github(token):
    """Sets up the GitHub Personal Access Token in the global config file."""
    config_file = os.path.join(get_config_dir(), "config")
    with open(config_file, "a") as f:
        f.write(f"GITHUB_TOKEN={token}\n")
    click.echo("GitHub Personal Access Token has been stored in global config file.")


if __name__ == "__main__":
    cli()
