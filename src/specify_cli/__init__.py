#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer",
#     "rich",
#     "platformdirs",
#     "readchar",
#     "httpx",
# ]
# ///
"""
Specify CLI - Specifyプロジェクトのセットアップツール

使用方法:
    uvx specify-cli.py init <プロジェクト名>
    uvx specify-cli.py init --here
    
またはグローバルインストール:
    uv tool install --from specify-cli.py specify-cli
    specify init <プロジェクト名>
    specify init --here
"""

import os
import subprocess
import sys
import zipfile
import tempfile
import shutil
import json
from pathlib import Path
from typing import Optional

import typer
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.table import Table
from rich.tree import Tree
from typer.core import TyperGroup

# For cross-platform keyboard input
import readchar

# Constants
AI_CHOICES = {
    "copilot": "GitHub Copilot",
    "claude": "Claude Code",
    "gemini": "Gemini CLI"
}

# ASCII Art Banner
BANNER = """
███████╗██████╗ ███████╗ ██████╗██╗███████╗██╗   ██╗
██╔════╝██╔══██╗██╔════╝██╔════╝██║██╔════╝╚██╗ ██╔╝
███████╗██████╔╝█████╗  ██║     ██║█████╗   ╚████╔╝ 
╚════██║██╔═══╝ ██╔══╝  ██║     ██║██╔══╝    ╚██╔╝  
███████║██║     ███████╗╚██████╗██║██║        ██║   
╚══════╝╚═╝     ╚══════╝ ╚═════╝╚═╝╚═╝        ╚═╝   
"""

TAGLINE = "仕様駆動開発ツールキット"
class StepTracker:
    """階層的なステップをトラッキングして表示。Claude Codeのツリー出力と同様のスタイル。
    アタッチされたリフレッシュコールバックによる自動更新をサポート。
    """
    def __init__(self, title: str):
        self.title = title
        self.steps = []  # list of dicts: {key, label, status, detail}
        self.status_order = {"pending": 0, "running": 1, "done": 2, "error": 3, "skipped": 4}
        self._refresh_cb = None  # callable to trigger UI refresh

    def attach_refresh(self, cb):
        self._refresh_cb = cb

    def add(self, key: str, label: str):
        if key not in [s["key"] for s in self.steps]:
            self.steps.append({"key": key, "label": label, "status": "pending", "detail": ""})
            self._maybe_refresh()

    def start(self, key: str, detail: str = ""):
        self._update(key, status="running", detail=detail)

    def complete(self, key: str, detail: str = ""):
        self._update(key, status="done", detail=detail)

    def error(self, key: str, detail: str = ""):
        self._update(key, status="error", detail=detail)

    def skip(self, key: str, detail: str = ""):
        self._update(key, status="skipped", detail=detail)

    def _update(self, key: str, status: str, detail: str):
        for s in self.steps:
            if s["key"] == key:
                s["status"] = status
                if detail:
                    s["detail"] = detail
                self._maybe_refresh()
                return
        # If not present, add it
        self.steps.append({"key": key, "label": key, "status": status, "detail": detail})
        self._maybe_refresh()

    def _maybe_refresh(self):
        if self._refresh_cb:
            try:
                self._refresh_cb()
            except Exception:
                pass

    def render(self):
        tree = Tree(f"[bold cyan]{self.title}[/bold cyan]", guide_style="grey50")
        for step in self.steps:
            label = step["label"]
            detail_text = step["detail"].strip() if step["detail"] else ""

            # Circles (unchanged styling)
            status = step["status"]
            if status == "done":
                symbol = "[green]●[/green]"
            elif status == "pending":
                symbol = "[green dim]○[/green dim]"
            elif status == "running":
                symbol = "[cyan]○[/cyan]"
            elif status == "error":
                symbol = "[red]●[/red]"
            elif status == "skipped":
                symbol = "[yellow]○[/yellow]"
            else:
                symbol = " "

            if status == "pending":
                # Entire line light gray (pending)
                if detail_text:
                    line = f"{symbol} [bright_black]{label} ({detail_text})[/bright_black]"
                else:
                    line = f"{symbol} [bright_black]{label}[/bright_black]"
            else:
                # Label white, detail (if any) light gray in parentheses
                if detail_text:
                    line = f"{symbol} [white]{label}[/white] [bright_black]({detail_text})[/bright_black]"
                else:
                    line = f"{symbol} [white]{label}[/white]"

            tree.add(line)
        return tree



MINI_BANNER = """
╔═╗╔═╗╔═╗╔═╗╦╔═╗╦ ╦
╚═╗╠═╝║╣ ║  ║╠╣ ╚╦╝
╚═╝╩  ╚═╝╚═╝╩╚   ╩ 
"""

def get_key():
    """Get a single keypress in a cross-platform way using readchar."""
    key = readchar.readkey()
    
    # Arrow keys
    if key == readchar.key.UP:
        return 'up'
    if key == readchar.key.DOWN:
        return 'down'
    
    # Enter/Return
    if key == readchar.key.ENTER:
        return 'enter'
    
    # Escape
    if key == readchar.key.ESC:
        return 'escape'
        
    # Ctrl+C
    if key == readchar.key.CTRL_C:
        raise KeyboardInterrupt

    return key



def select_with_arrows(options: dict, prompt_text: str = "Select an option", default_key: str = None) -> str:
    """
    Interactive selection using arrow keys with Rich Live display.
    
    Args:
        options: Dict with keys as option keys and values as descriptions
        prompt_text: Text to show above the options
        default_key: Default option key to start with
        
    Returns:
        Selected option key
    """
    option_keys = list(options.keys())
    if default_key and default_key in option_keys:
        selected_index = option_keys.index(default_key)
    else:
        selected_index = 0
    
    selected_key = None

    def create_selection_panel():
        """Create the selection panel with current selection highlighted."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bright_cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")
        
        for i, key in enumerate(option_keys):
            if i == selected_index:
                table.add_row("▶", f"[bright_cyan]{key}: {options[key]}[/bright_cyan]")
            else:
                table.add_row(" ", f"[white]{key}: {options[key]}[/white]")
        
        table.add_row("", "")
        table.add_row("", "[dim]Use ↑/↓ to navigate, Enter to select, Esc to cancel[/dim]")
        
        return Panel(
            table,
            title=f"[bold]{prompt_text}[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    console.print()

    def run_selection_loop():
        nonlocal selected_key, selected_index
        with Live(create_selection_panel(), console=console, transient=True, auto_refresh=False) as live:
            while True:
                try:
                    key = get_key()
                    if key == 'up':
                        selected_index = (selected_index - 1) % len(option_keys)
                    elif key == 'down':
                        selected_index = (selected_index + 1) % len(option_keys)
                    elif key == 'enter':
                        selected_key = option_keys[selected_index]
                        break
                    elif key == 'escape':
                        console.print("\n[yellow]Selection cancelled[/yellow]")
                        raise typer.Exit(1)
                    
                    live.update(create_selection_panel(), refresh=True)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

    run_selection_loop()

    if selected_key is None:
        console.print("\n[red]Selection failed.[/red]")
        raise typer.Exit(1)

    # Suppress explicit selection print; tracker / later logic will report consolidated status
    return selected_key



console = Console()


class BannerGroup(TyperGroup):
    """Custom group that shows banner before help."""
    
    def format_help(self, ctx, formatter):
        # Show banner before help
        show_banner()
        super().format_help(ctx, formatter)


app = typer.Typer(
    name="specify",
    help="Specify仕様駆動開発プロジェクトのセットアップツール",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)


def show_banner():
    """Display the ASCII art banner."""
    # Create gradient effect with different colors
    banner_lines = BANNER.strip().split('\n')
    colors = ["bright_blue", "blue", "cyan", "bright_cyan", "white", "bright_white"]
    
    styled_banner = Text()
    for i, line in enumerate(banner_lines):
        color = colors[i % len(colors)]
        styled_banner.append(line + "\n", style=color)
    
    console.print(Align.center(styled_banner))
    console.print(Align.center(Text(TAGLINE, style="italic bright_yellow")))
    console.print()


@app.callback()
def callback(ctx: typer.Context):
    """サブコマンドが提供されない場合にバナーを表示。"""
    # Show banner only when no subcommand and no help flag
    # (help is handled by BannerGroup)
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]使用方法については 'specify --help' を実行してください[/dim]"))
        console.print()


def run_command(cmd: list[str], check_return: bool = True, capture: bool = False, shell: bool = False) -> Optional[str]:
    """Run a shell command and optionally capture output."""
    try:
        if capture:
            result = subprocess.run(cmd, check=check_return, capture_output=True, text=True, shell=shell)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check_return, shell=shell)
            return None
    except subprocess.CalledProcessError as e:
        if check_return:
            console.print(f"[red]Error running command:[/red] {' '.join(cmd)}")
            console.print(f"[red]Exit code:[/red] {e.returncode}")
            if hasattr(e, 'stderr') and e.stderr:
                console.print(f"[red]Error output:[/red] {e.stderr}")
            raise
        return None


def check_tool(tool: str, install_hint: str) -> bool:
    """ツールがインストールされているか確認。"""
    if shutil.which(tool):
        return True
    else:
        console.print(f"[yellow]⚠️  {tool} が見つかりません[/yellow]")
        console.print(f"   インストール方法: [cyan]{install_hint}[/cyan]")
        return False


def is_git_repo(path: Path = None) -> bool:
    """Check if the specified path is inside a git repository."""
    if path is None:
        path = Path.cwd()
    
    if not path.is_dir():
        return False

    try:
        # Use git command to check if inside a work tree
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            cwd=path,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def init_git_repo(project_path: Path, quiet: bool = False) -> bool:
    """Initialize a git repository in the specified path.
    quiet: if True suppress console output (tracker handles status)
    """
    try:
        original_cwd = Path.cwd()
        os.chdir(project_path)
        if not quiet:
            console.print("[cyan]Gitリポジトリを初期化中...[/cyan]")
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Specifyテンプレートからの初回コミット"], check=True, capture_output=True)
        if not quiet:
            console.print("[green]✓[/green] Gitリポジトリを初期化しました")
        return True
        
    except subprocess.CalledProcessError as e:
        if not quiet:
            console.print(f"[red]Gitリポジトリの初期化エラー:[/red] {e}")
        return False
    finally:
        os.chdir(original_cwd)


def download_template_from_github(ai_assistant: str, download_dir: Path, *, verbose: bool = True, show_progress: bool = True):
    """Download the latest template release from GitHub using HTTP requests.
    Returns (zip_path, metadata_dict)
    """
    repo_owner = "github"
    repo_name = "spec-kit"
    
    if verbose:
        console.print("[cyan]最新リリース情報を取得中...[/cyan]")
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    
    try:
        response = httpx.get(api_url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        release_data = response.json()
    except httpx.RequestError as e:
        if verbose:
            console.print(f"[red]リリース情報の取得エラー:[/red] {e}")
        raise typer.Exit(1)
    
    # Find the template asset for the specified AI assistant
    pattern = f"spec-kit-template-{ai_assistant}"
    matching_assets = [
        asset for asset in release_data.get("assets", [])
        if pattern in asset["name"] and asset["name"].endswith(".zip")
    ]
    
    if not matching_assets:
        if verbose:
            console.print(f"[red]エラー:[/red] AIアシスタント '{ai_assistant}' 用のテンプレートが見つかりません")
            console.print(f"[yellow]利用可能なアセット:[/yellow]")
            for asset in release_data.get("assets", []):
                console.print(f"  - {asset['name']}")
        raise typer.Exit(1)
    
    # Use the first matching asset
    asset = matching_assets[0]
    download_url = asset["browser_download_url"]
    filename = asset["name"]
    file_size = asset["size"]
    
    if verbose:
        console.print(f"[cyan]テンプレートを発見:[/cyan] {filename}")
        console.print(f"[cyan]サイズ:[/cyan] {file_size:,} バイト")
        console.print(f"[cyan]リリース:[/cyan] {release_data['tag_name']}")
    
    # Download the file
    zip_path = download_dir / filename
    if verbose:
        console.print(f"[cyan]テンプレートをダウンロード中...[/cyan]")
    
    try:
        with httpx.stream("GET", download_url, timeout=30, follow_redirects=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(zip_path, 'wb') as f:
                if total_size == 0:
                    # No content-length header, download without progress
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                else:
                    if show_progress:
                        # Show progress bar
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[progress.description]{task.description}"),
                            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                            console=console,
                        ) as progress:
                            task = progress.add_task("ダウンロード中...", total=total_size)
                            downloaded = 0
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                progress.update(task, completed=downloaded)
                    else:
                        # Silent download loop
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
    
    except httpx.RequestError as e:
        if verbose:
            console.print(f"[red]テンプレートのダウンロードエラー:[/red] {e}")
        if zip_path.exists():
            zip_path.unlink()
        raise typer.Exit(1)
    if verbose:
        console.print(f"ダウンロード完了: {filename}")
    metadata = {
        "filename": filename,
        "size": file_size,
        "release": release_data["tag_name"],
        "asset_url": download_url
    }
    return zip_path, metadata


def download_and_extract_template(project_path: Path, ai_assistant: str, is_current_dir: bool = False, *, verbose: bool = True, tracker: StepTracker | None = None) -> Path:
    """Download the latest release and extract it to create a new project.
    Returns project_path. Uses tracker if provided (with keys: fetch, download, extract, cleanup)
    """
    current_dir = Path.cwd()
    
    # Step: fetch + download combined
    if tracker:
        tracker.start("fetch", "contacting GitHub API")
    try:
        zip_path, meta = download_template_from_github(
            ai_assistant,
            current_dir,
            verbose=verbose and tracker is None,
            show_progress=(tracker is None)
        )
        if tracker:
            tracker.complete("fetch", f"release {meta['release']} ({meta['size']:,} bytes)")
            tracker.add("download", "Download template")
            tracker.complete("download", meta['filename'])  # already downloaded inside helper
    except Exception as e:
        if tracker:
            tracker.error("fetch", str(e))
        else:
            if verbose:
                console.print(f"[red]テンプレートのダウンロードエラー:[/red] {e}")
        raise
    
    if tracker:
        tracker.add("extract", "Extract template")
        tracker.start("extract")
    elif verbose:
        console.print("テンプレートを展開中...")
    
    try:
        # Create project directory only if not using current directory
        if not is_current_dir:
            project_path.mkdir(parents=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List all files in the ZIP for debugging
            zip_contents = zip_ref.namelist()
            if tracker:
                tracker.start("zip-list")
                tracker.complete("zip-list", f"{len(zip_contents)} entries")
            elif verbose:
                console.print(f"[cyan]ZIPには{len(zip_contents)}個のアイテムが含まれています[/cyan]")
            
            # For current directory, extract to a temp location first
            if is_current_dir:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    zip_ref.extractall(temp_path)
                    
                    # Check what was extracted
                    extracted_items = list(temp_path.iterdir())
                    if tracker:
                        tracker.start("extracted-summary")
                        tracker.complete("extracted-summary", f"temp {len(extracted_items)} items")
                    elif verbose:
                        console.print(f"[cyan]{len(extracted_items)}個のアイテムを一時フォルダに展開[/cyan]")
                    
                    # Handle GitHub-style ZIP with a single root directory
                    source_dir = temp_path
                    if len(extracted_items) == 1 and extracted_items[0].is_dir():
                        source_dir = extracted_items[0]
                        if tracker:
                            tracker.add("flatten", "Flatten nested directory")
                            tracker.complete("flatten")
                        elif verbose:
                            console.print(f"[cyan]ネストされたディレクトリ構造を発見[/cyan]")
                    
                    # Copy contents to current directory
                    for item in source_dir.iterdir():
                        dest_path = project_path / item.name
                        if item.is_dir():
                            if dest_path.exists():
                                if verbose and not tracker:
                                    console.print(f"[yellow]ディレクトリをマージ中:[/yellow] {item.name}")
                                # Recursively copy directory contents
                                for sub_item in item.rglob('*'):
                                    if sub_item.is_file():
                                        rel_path = sub_item.relative_to(item)
                                        dest_file = dest_path / rel_path
                                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                                        shutil.copy2(sub_item, dest_file)
                            else:
                                shutil.copytree(item, dest_path)
                        else:
                            if dest_path.exists() and verbose and not tracker:
                                console.print(f"[yellow]ファイルを上書き:[/yellow] {item.name}")
                            shutil.copy2(item, dest_path)
                    if verbose and not tracker:
                        console.print(f"[cyan]テンプレートファイルを現在のディレクトリにマージしました[/cyan]")
            else:
                # Extract directly to project directory (original behavior)
                zip_ref.extractall(project_path)
                
                # Check what was extracted
                extracted_items = list(project_path.iterdir())
                if tracker:
                    tracker.start("extracted-summary")
                    tracker.complete("extracted-summary", f"{len(extracted_items)} top-level items")
                elif verbose:
                    console.print(f"[cyan]{len(extracted_items)}個のアイテムを{project_path}に展開:[/cyan]")
                    for item in extracted_items:
                        console.print(f"  - {item.name} ({'ディレクトリ' if item.is_dir() else 'ファイル'})")
                
                # Handle GitHub-style ZIP with a single root directory
                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    # Move contents up one level
                    nested_dir = extracted_items[0]
                    temp_move_dir = project_path.parent / f"{project_path.name}_temp"
                    # Move the nested directory contents to temp location
                    shutil.move(str(nested_dir), str(temp_move_dir))
                    # Remove the now-empty project directory
                    project_path.rmdir()
                    # Rename temp directory to project directory
                    shutil.move(str(temp_move_dir), str(project_path))
                    if tracker:
                        tracker.add("flatten", "Flatten nested directory")
                        tracker.complete("flatten")
                    elif verbose:
                        console.print(f"[cyan]ネストされたディレクトリ構造をフラット化しました[/cyan]")
                    
    except Exception as e:
        if tracker:
            tracker.error("extract", str(e))
        else:
            if verbose:
                console.print(f"[red]テンプレートの展開エラー:[/red] {e}")
        # Clean up project directory if created and not current directory
        if not is_current_dir and project_path.exists():
            shutil.rmtree(project_path)
        raise typer.Exit(1)
    else:
        if tracker:
            tracker.complete("extract")
    finally:
        if tracker:
            tracker.add("cleanup", "Remove temporary archive")
        # Clean up downloaded ZIP file
        if zip_path.exists():
            zip_path.unlink()
            if tracker:
                tracker.complete("cleanup")
            elif verbose:
                console.print(f"クリーンアップ完了: {zip_path.name}")
    
    return project_path


@app.command()
def init(
    project_name: str = typer.Argument(None, help="新しいプロジェクトディレクトリの名前（--here使用時はオプション）"),
    ai_assistant: str = typer.Option(None, "--ai", help="使用するAIアシスタント: claude, gemini, または copilot"),
    ignore_agent_tools: bool = typer.Option(False, "--ignore-agent-tools", help="Claude CodeなどのAIエージェントツールのチェックをスキップ"),
    no_git: bool = typer.Option(False, "--no-git", help="gitリポジトリの初期化をスキップ"),
    here: bool = typer.Option(False, "--here", help="新しいディレクトリを作成せず、現在のディレクトリでプロジェクトを初期化"),
):
    """
    最新のテンプレートから新しいSpecifyプロジェクトを初期化します。
    
    このコマンドは以下を実行します:
    1. 必要なツールがインストールされているか確認（gitはオプション）
    2. AIアシスタントを選択（Claude Code、Gemini CLI、またはGitHub Copilot）
    3. GitHubから適切なテンプレートをダウンロード
    4. テンプレートを新しいプロジェクトディレクトリまたは現在のディレクトリに展開
    5. 新しいgitリポジトリを初期化（--no-gitが指定されず、既存のリポジトリがない場合）
    6. AIアシスタントコマンドをオプションで設定
    
    例:
        specify init my-project
        specify init my-project --ai claude
        specify init my-project --ai gemini
        specify init my-project --ai copilot --no-git
        specify init --ignore-agent-tools my-project
        specify init --here --ai claude
        specify init --here
    """
    # Show banner first
    show_banner()
    
    # Validate arguments
    if here and project_name:
        console.print("[red]エラー:[/red] プロジェクト名と--hereフラグを同時に指定できません")
        raise typer.Exit(1)
    
    if not here and not project_name:
        console.print("[red]エラー:[/red] プロジェクト名を指定するか、--hereフラグを使用してください")
        raise typer.Exit(1)
    
    # Determine project directory
    if here:
        project_name = Path.cwd().name
        project_path = Path.cwd()
        
        # Check if current directory has any files
        existing_items = list(project_path.iterdir())
        if existing_items:
            console.print(f"[yellow]警告:[/yellow] 現在のディレクトリは空ではありません（{len(existing_items)}個のアイテム）")
            console.print("[yellow]テンプレートファイルは既存のコンテンツとマージされ、既存のファイルを上書きする可能性があります[/yellow]")
            
            # Ask for confirmation
            response = typer.confirm("続行しますか？")
            if not response:
                console.print("[yellow]操作がキャンセルされました[/yellow]")
                raise typer.Exit(0)
    else:
        project_path = Path(project_name).resolve()
        # Check if project directory already exists
        if project_path.exists():
            console.print(f"[red]エラー:[/red] ディレクトリ '{project_name}' は既に存在します")
            raise typer.Exit(1)
    
    console.print(Panel.fit(
        "[bold cyan]Specifyプロジェクトセットアップ[/bold cyan]\n"
        f"{'現在のディレクトリで初期化:' if here else '新しいプロジェクトを作成:'} [green]{project_path.name}[/green]"
        + (f"\n[dim]パス: {project_path}[/dim]" if here else ""),
        border_style="cyan"
    ))
    
    # Check git only if we might need it (not --no-git)
    git_available = True
    if not no_git:
        git_available = check_tool("git", "https://git-scm.com/downloads")
        if not git_available:
            console.print("[yellow]Gitが見つかりません - リポジトリの初期化をスキップします[/yellow]")

    # AI assistant selection
    if ai_assistant:
        if ai_assistant not in AI_CHOICES:
            console.print(f"[red]エラー:[/red] 無効なAIアシスタント '{ai_assistant}'。次から選択してください: {', '.join(AI_CHOICES.keys())}")
            raise typer.Exit(1)
        selected_ai = ai_assistant
    else:
        # Use arrow-key selection interface
        selected_ai = select_with_arrows(
            AI_CHOICES, 
            "AIアシスタントを選択:", 
            "copilot"
        )
    
    # Check agent tools unless ignored
    if not ignore_agent_tools:
        agent_tool_missing = False
        if selected_ai == "claude":
            if not check_tool("claude", "Install from: https://docs.anthropic.com/en/docs/claude-code/setup"):
                console.print("[red]エラー:[/red] Claude CodeプロジェクトにはClaude CLIが必要です")
                agent_tool_missing = True
        elif selected_ai == "gemini":
            if not check_tool("gemini", "Install from: https://github.com/google-gemini/gemini-cli"):
                console.print("[red]エラー:[/red] GeminiプロジェクトにはGemini CLIが必要です")
                agent_tool_missing = True
        # GitHub Copilot check is not needed as it's typically available in supported IDEs
        
        if agent_tool_missing:
            console.print("\n[red]必要なAIツールがありません！[/red]")
            console.print("[yellow]ヒント:[/yellow] --ignore-agent-toolsを使用してこのチェックをスキップできます")
            raise typer.Exit(1)
    
    # Download and set up project
    # New tree-based progress (no emojis); include earlier substeps
    tracker = StepTracker("Specifyプロジェクトの初期化")
    # Flag to allow suppressing legacy headings
    sys._specify_tracker_active = True
    # Pre steps recorded as completed before live rendering
    tracker.add("precheck", "必要なツールを確認")
    tracker.complete("precheck", "OK")
    tracker.add("ai-select", "AIアシスタントを選択")
    tracker.complete("ai-select", f"{selected_ai}")
    for key, label in [
        ("fetch", "最新リリースを取得"),
        ("download", "テンプレートをダウンロード"),
        ("extract", "テンプレートを展開"),
        ("zip-list", "アーカイブの内容"),
        ("extracted-summary", "展開の要約"),
        ("cleanup", "クリーンアップ"),
        ("git", "Gitリポジトリを初期化"),
        ("final", "完了")
    ]:
        tracker.add(key, label)

    # Use transient so live tree is replaced by the final static render (avoids duplicate output)
    with Live(tracker.render(), console=console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))
        try:
            download_and_extract_template(project_path, selected_ai, here, verbose=False, tracker=tracker)

            # Git step
            if not no_git:
                tracker.start("git")
                if is_git_repo(project_path):
                    tracker.complete("git", "既存のリポジトリを検出")
                elif git_available:
                    if init_git_repo(project_path, quiet=True):
                        tracker.complete("git", "初期化完了")
                    else:
                        tracker.error("git", "初期化失敗")
                else:
                    tracker.skip("git", "gitが利用できません")
            else:
                tracker.skip("git", "--no-gitフラグ")

            tracker.complete("final", "プロジェクト準備完了")
        except Exception as e:
            tracker.error("final", str(e))
            if not here and project_path.exists():
                shutil.rmtree(project_path)
            raise typer.Exit(1)
        finally:
            # Force final render
            pass

    # Final static tree (ensures finished state visible after Live context ends)
    console.print(tracker.render())
    console.print("\n[bold green]プロジェクトの準備が完了しました。[/bold green]")
    
    # Boxed "Next steps" section
    steps_lines = []
    if not here:
        steps_lines.append(f"1. [bold green]cd {project_name}[/bold green]")
        step_num = 2
    else:
        steps_lines.append("1. 既にプロジェクトディレクトリにいます！")
        step_num = 2

    if selected_ai == "claude":
        steps_lines.append(f"{step_num}. Visual Studio Codeで開いて、Claude Codeで / コマンドを使用開始")
        steps_lines.append("   - 任意のファイルで / を入力して利用可能なコマンドを確認")
        steps_lines.append("   - /spec で仕様書を作成")
        steps_lines.append("   - /plan で実装計画を作成")
        steps_lines.append("   - /tasks でタスクを生成")
    elif selected_ai == "gemini":
        steps_lines.append(f"{step_num}. Gemini CLIで / コマンドを使用")
        steps_lines.append("   - gemini /spec を実行して仕様書を作成")
        steps_lines.append("   - gemini /plan を実行して実装計画を作成")
        steps_lines.append("   - GEMINI.mdですべての利用可能なコマンドを確認")
    elif selected_ai == "copilot":
        steps_lines.append(f"{step_num}. Visual Studio Codeで開いて、GitHub Copilotで [bold cyan]/specify[/], [bold cyan]/plan[/], [bold cyan]/tasks[/] コマンドを使用")

    step_num += 1
    steps_lines.append(f"{step_num}. [bold magenta]CONSTITUTION.md[/bold magenta] をプロジェクトの譲論の余地のない原則で更新")

    steps_panel = Panel("\n".join(steps_lines), title="次のステップ", border_style="cyan", padding=(1,2))
    console.print()  # blank line
    console.print(steps_panel)
    
    # Removed farewell line per user request


@app.command()
def check():
    """すべての必要なツールがインストールされているか確認します。"""
    show_banner()
    console.print("[bold]Specifyの要件を確認中...[/bold]\n")
    
    # Check if we have internet connectivity by trying to reach GitHub API
    console.print("[cyan]インターネット接続を確認中...[/cyan]")
    try:
        response = httpx.get("https://api.github.com", timeout=5, follow_redirects=True)
        console.print("[green]✓[/green] インターネット接続が利用可能です")
    except httpx.RequestError:
        console.print("[red]✗[/red] インターネット接続がありません - テンプレートのダウンロードに必要です")
        console.print("[yellow]インターネット接続を確認してください[/yellow]")
    
    console.print("\n[cyan]オプションツール:[/cyan]")
    git_ok = check_tool("git", "https://git-scm.com/downloads")
    
    console.print("\n[cyan]オプションAIツール:[/cyan]")
    claude_ok = check_tool("claude", "Install from: https://docs.anthropic.com/en/docs/claude-code/setup")
    gemini_ok = check_tool("gemini", "Install from: https://github.com/google-gemini/gemini-cli")
    
    console.print("\n[green]✓ Specify CLIは使用可能です！[/green]")
    if not git_ok:
        console.print("[yellow]リポジトリ管理のためにgitのインストールを検討してください[/yellow]")
    if not (claude_ok or gemini_ok):
        console.print("[yellow]最良の体験のためにAIアシスタントのインストールを検討してください[/yellow]")


def main():
    app()


if __name__ == "__main__":
    main()