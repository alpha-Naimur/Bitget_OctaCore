"""Interactive Terminal CLI interface for Bitget OctaCore using Rich."""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text

from src.core.orchestrator import orchestrator
from src.core.config import settings
from src.bitget.client import bitget_client
from src.bitget.oauth import oauth_manager
from src.bitget.trading_engine import trading_engine
from src.bitget.market_data import market_data
from src.bitget.sub_account import sub_account_manager
from bitget_skills_hub.tokenized_stocks.tools import scan_tokenized_stocks
from bitget_skills_hub.backtesting.tools import run_strategy_backtest
from bitget_skills_hub.quant_engine.tools import get_quant_risk_metrics, get_time_series_regime

console = Console()


def print_banner():
    auth_status = bitget_client.get_auth_status()
    auth_style = "green" if auth_status["authenticated"] else "red"
    auth_label = f"OAuth Active ({auth_status['auth_source']})" if auth_status["authenticated"] else "UNAUTHORIZED (run 'login')"

    banner = Text()
    banner.append("⚡ BITGET OCTACORE ⚡\n", style="bold cyan")
    banner.append("Institutional 8-Core Autonomous AI Trading Operating System\n", style="bold white")
    banner.append("Bitget AI Base Camp Hackathon S2 — Track 2: Agentic Trading\n", style="dim cyan")
    banner.append(
        f"Mode: {settings.EXECUTION_MODE.value} | UID: {sub_account_manager.get_display_uid()} | "
        f"Auth: [{auth_style}]{auth_label}[/{auth_style}] | LLM: {settings.LLM_PROVIDER.value}\n",
        style="yellow"
    )
    console.print(Panel(banner, border_style="cyan", expand=False))


def display_portfolio():
    p = trading_engine.get_portfolio()
    table = Table(title=f"Portfolio Telemetry ({p.get('mode', 'SIMULATION')})", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Total Valuation", f"${p.get('total_value_usdt', 0.0):,.2f} USDT")
    table.add_row("Available Cash", f"${p.get('available_usdt', 0.0):,.2f} USDT")
    table.add_row("Realized PnL", f"${p.get('realized_pnl', 0.0):,.2f}")
    table.add_row("Unrealized PnL", f"${p.get('unrealized_pnl', 0.0):,.2f}")
    table.add_row("Total Return %", f"{p.get('total_pnl_percent', 0.0):+.2f}%")
    table.add_row("Kill-Switch Active", str(p.get("kill_switch_active", False)))

    console.print(table)


def display_us_stocks():
    stocks = scan_tokenized_stocks()
    table = Table(title="7x24 Continuous Tokenized US Equities Radar", border_style="green")
    table.add_column("Symbol", style="bold white")
    table.add_column("Price (USDT)", style="cyan")
    table.add_column("24h Change", style="yellow")
    table.add_column("RSI (14)", style="magenta")
    table.add_column("Bias", style="bold")
    table.add_column("Market Hours", style="dim")

    for s in stocks.get("stocks", []):
        chg_style = "green" if s.get("change_24h", 0) >= 0 else "red"
        bias_style = "green" if s.get("bias") == "BULLISH" else ("red" if s.get("bias") == "BEARISH" else "yellow")
        pr = float(s.get("price") or 0.0)
        chg = float(s.get("change_24h") or 0.0)
        rsi_val = float(s.get("rsi") or 50.0)
        table.add_row(
            str(s.get("symbol", "N/A")),
            f"${pr:.2f}",
            f"[{chg_style}]{chg:+.2f}%[/{chg_style}]",
            f"{rsi_val:.1f}",
            f"[{bias_style}]{s.get('bias', 'NEUTRAL')}[/{bias_style}]",
            "7x24 Active"
        )

    console.print(table)


def run_cli_loop():
    print_banner()
    console.print("[dim]Commands: 'login' (Bitget OAuth), 'auth' (status), 'logout', 'scan', 'portfolio', 'kill', 'exit'[/dim]\n")

    while True:
        try:
            cmd = Prompt.ask("[bold cyan]OctaCore ❯[/bold cyan]").strip()
            if not cmd:
                continue

            if cmd.lower() in ("exit", "quit"):
                console.print("[yellow]Exiting Bitget OctaCore CLI...[/yellow]")
                break

            elif cmd.lower() in ("login", "oauth"):
                console.print("\n[bold cyan]🔑 Initiating Bitget Agentic Account OAuth 2.0 Flow...[/bold cyan]")
                with console.status("[cyan]Generating ephemeral RSA-2048 keypair and starting callback listener...[/cyan]"):
                    start_res = oauth_manager.start_oauth_flow()
                session_id = start_res["session_id"]
                auth_url = start_res["authorize_url"]
                port = start_res["callback_port"]

                console.print(Panel(
                    f"[bold green]OAuth Callback Listener Running on port {port}[/bold green]\n\n"
                    f"Opening Bitget authorization in your browser:\n"
                    f"[cyan]{auth_url}[/cyan]\n\n"
                    "[yellow]Steps on Bitget:[/yellow]\n"
                    "1. Sign in to your KYC-verified Bitget account\n"
                    "2. Choose [bold]'Create new'[/bold] or [bold]'Use existing'[/bold] Agentic sub-account\n"
                    "3. Click [bold]'Allow'[/bold] and complete 2FA on the Bitget Mobile App\n",
                    title="Bitget Agentic OAuth",
                    border_style="cyan"
                ))

                import webbrowser
                try:
                    webbrowser.open(auth_url)
                except Exception:
                    console.print("[yellow]Please open the URL above manually in your browser.[/yellow]")

                with console.status("[yellow]Awaiting OAuth callback from browser (up to 5 min)...[/yellow]", spinner="earth"):
                    auth_res = oauth_manager.wait_for_oauth_callback(session_id, timeout_seconds=300.0)

                if auth_res.get("success"):
                    bitget_client.reload_credentials()
                    console.print(Panel(
                        f"[bold green]✔ Bitget Agentic Sub-Account Successfully Authorized![/bold green]\n\n"
                        f"Sub-Account UID: [cyan]{auth_res.get('user_id')}[/cyan]\n"
                        f"Masked API Key: [yellow]{auth_res.get('api_key_masked')}[/yellow]\n"
                        f"Obtained At: {auth_res.get('obtained_at')}\n"
                        f"Token Location: [dim]{auth_res.get('credentials_file')}[/dim]\n"
                        f"Safety Constraint: [green]Non-withdrawal isolated fund sandbox[/green]",
                        title="🎉 Authorization Success",
                        border_style="green"
                    ))
                else:
                    console.print(f"[bold red]❌ OAuth Failed: {auth_res.get('error')}[/bold red]")

            elif cmd.lower() in ("auth", "status", "whoami"):
                status = oauth_manager.get_auth_status()
                table = Table(title="Bitget Agentic Account Authentication Status", border_style="cyan")
                table.add_column("Property", style="bold")
                table.add_column("Value", style="cyan")
                table.add_row("Authorized", "[green]Yes[/green]" if status.get("authorized") else "[red]No[/red]")
                table.add_row("Auth Type", str(status.get("auth_type")))
                table.add_row("Agentic UID", str(status.get("user_id", "N/A")))
                table.add_row("Masked API Key", str(status.get("api_key_masked", "N/A")))
                table.add_row("Obtained At", str(status.get("obtained_at", "N/A")))
                table.add_row("Credentials Path", str(status.get("credentials_file", "N/A")))
                console.print(table)

            elif cmd.lower() == "logout":
                if oauth_manager.revoke_credentials():
                    bitget_client.reload_credentials()
                    console.print("[yellow]✔ Successfully logged out. Local OAuth credentials removed.[/yellow]")
                else:
                    console.print("[red]Failed to remove credentials file.[/red]")

            elif cmd.lower() == "portfolio":
                display_portfolio()

            elif cmd.lower() in ("scan", "stocks"):
                display_us_stocks()

            elif cmd.lower() == "kill":
                res = trading_engine.trigger_kill_switch()
                console.print("[bold red]🚨 EMERGENCY KILL-SWITCH ENGAGED! All positions liquidated to USDT.[/bold red]")

            else:
                with console.status("[bold cyan]OctaCore Cores Thinking & Executing...[/bold cyan]", spinner="dots"):
                    result = orchestrator.process_command(cmd)

                console.print(Panel(
                    result.get("response", "Command processed."),
                    title=f"🤖 OctaCore Synthesis ({result.get('provider')})",
                    border_style="cyan"
                ))

                if result.get("tool_calls"):
                    t_table = Table(title="Executed Specialist Tools", border_style="dim")
                    t_table.add_column("Tool Name", style="bold magenta")
                    t_table.add_column("Arguments", style="dim")
                    for tc in result.get("tool_calls"):
                        t_table.add_row(tc.get("tool_name"), str(tc.get("args")))
                    console.print(t_table)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session interrupted. Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
    run_cli_loop()
