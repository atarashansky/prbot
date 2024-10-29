import click
from github import Github
from git import Repo
import openai
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


@click.group()
def cli():
    pass


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
    openai.api_key = os.getenv("OPENAI_API_KEY")

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_file.write(diff)
        temp_file.flush()

        try:
            response = openai.File.create(
                file=open(temp_file.name, "rb"), purpose="assistants"
            )
            file_id = response.id

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates PR descriptions based on git diffs.",
                },
                {
                    "role": "user",
                    "content": f"Please generate a concise PR description based on the git diff in the uploaded file. The branch name is {branch_name}.",
                },
            ]

            response = openai.ChatCompletion.create(
                model="gpt-4o", messages=messages, file_ids=[file_id]
            )

            pr_description = response.choices[0].message.content

            click.echo(f"Generated PR description:\n\n{pr_description}")

            # (Optional) Update or create a PR on GitHub
            # pr = repo.create_pull(title=f"PR for {branch_name}", body=pr_description, head=branch_name, base="main")
            # click.echo(f"Created PR: {pr.html_url}")

        finally:
            os.unlink(temp_file.name)
            openai.File.delete(file_id)


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
