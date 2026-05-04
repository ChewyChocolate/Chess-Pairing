import os
import logging
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Input, Label, ListItem, ListView, RadioButton, RadioSet, Static, TextArea
from textual.widgets.data_table import RowDoesNotExist

from player import Player
from tournament import Tournament, TournamentType
from errors import TournamentError

SAVE_FILE = "tournament_data.json"
CSV_FILE = "standings.csv"
HTML_FILE = "standings.html"
PLAYER_FILE = "players.txt"

CSS = """
Screen {
    layout: grid;
    grid-size: 2;
    grid-rows: 1fr auto;
    grid-gutter: 1;
    padding: 0 1;
}
.panel { border: solid $primary 30%; }
.panel-title { text-align: center; background: $surface; text-style: bold; padding: 0 1; height: 1; }
DataTable { height: 1fr; }
Footer { column-span: 2; }

#setup-center { align: center middle; width: 60; }
#setup-center > * { margin: 0 1; }
#player-input { height: 10; }
"""


class AddPlayerDialog(ModalScreen):
    def compose(self):
        yield Static("Add Player")
        yield Input(placeholder="Player name", id="player-name")
        with Horizontal():
            yield Button("Add", variant="primary", id="add")
            yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event):
        if event.button.id == "add":
            self._submit()
        elif event.button.id == "cancel":
            self.dismiss(None)

    def on_input_submitted(self):
        self._submit()

    def _submit(self):
        name = self.query_one("#player-name", Input).value.strip()
        if name:
            try:
                Player(name)
            except TournamentError as e:
                self.notify(str(e), severity="error")
                return
            self.dismiss(name)


class WithdrawDialog(ModalScreen):
    def __init__(self, players):
        super().__init__()
        self.players = players

    def compose(self):
        yield Static("Select player to withdraw:")
        items = []
        for p in self.players:
            if p.active:
                item = ListItem(Label(p.name))
                item._player = p
                items.append(item)
        yield ListView(*items, id="player-list")
        yield Button("Cancel", variant="default", id="cancel")

    def on_list_view_selected(self, event):
        self.dismiss(event.item._player)

    def on_button_pressed(self, event):
        if event.button.id == "cancel":
            self.dismiss(None)


class SetupScreen(Screen):
    def compose(self):
        with Vertical(id="setup-center"):
            yield Static("Chess Tournament Pairing System")
            if os.path.exists(SAVE_FILE):
                yield Button("Load existing tournament", variant="primary", id="load")
            yield Button("Create new tournament", variant="default", id="create")
            yield Button("Quit", variant="error", id="quit")

    def on_button_pressed(self, event):
        if event.button.id == "load":
            try:
                self.dismiss(Tournament.load_from_file(SAVE_FILE))
            except Exception as e:
                self.notify(str(e), severity="error")
        elif event.button.id == "create":
            self.app.push_screen(CreateTournamentScreen(), self._on_created)
        elif event.button.id == "quit":
            self.dismiss(None)

    def _on_created(self, t):
        if t is not None:
            self.dismiss(t)


class CreateTournamentScreen(Screen):
    def compose(self):
        with Vertical(id="setup-center"):
            yield Static("Create Tournament")
            yield Static("Enter one player name per line:")
            yield TextArea(id="player-input")
            with Horizontal():
                yield Button("Import", variant="default", id="import")
                yield Button("Export", variant="default", id="export")
            yield Static("Format:")
            with RadioSet(id="format"):
                yield RadioButton("Swiss")
                yield RadioButton("Round Robin")
            yield Button("Create", variant="primary", id="create")
            yield Button("Cancel", variant="default", id="cancel")

    @on(RadioSet.Changed)
    def _on_format_changed(self, event: RadioSet.Changed):
        event.stop()

    def on_button_pressed(self, event):
        if event.button.id == "import":
            self._do_import()
        elif event.button.id == "export":
            self._do_export()
        elif event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id != "create":
            return
        else:
            self._do_create()

    def _do_import(self):
        def cb(path):
            if not path:
                return
            try:
                with open(path) as f:
                    ta = self.query_one("#player-input", TextArea)
                    existing = [l for l in ta.text.split("\n") if l.strip()]
                    names = [l.strip() for l in f if l.strip()]
                    existing.extend(names)
                    ta.text = "\n".join(existing)
                    self.notify(f"Imported {len(names)} players")
            except FileNotFoundError:
                self.notify(f"File not found: {path}", severity="error")
            except Exception as e:
                self.notify(str(e), severity="error")
        self.app.push_screen(FileInputDialog("Import from file:", PLAYER_FILE), cb)

    def _do_export(self):
        def cb(path):
            if not path:
                return
            try:
                ta = self.query_one("#player-input", TextArea)
                names = [l.strip() for l in ta.text.split("\n") if l.strip()]
                with open(path, "w") as f:
                    f.write("\n".join(names) + "\n")
                self.notify(f"Exported {len(names)} players to {path}")
            except Exception as e:
                self.notify(str(e), severity="error")
        self.app.push_screen(FileInputDialog("Export to file:", PLAYER_FILE), cb)

    def _do_create(self):
        rs = self.query_one("#format", RadioSet)
        if rs.pressed_index < 0:
            self.notify("Select a format", severity="error")
            return
        t_type = TournamentType.SWISS if rs.pressed_index == 0 else TournamentType.ROUND_ROBIN
        text = self.query_one("#player-input", TextArea).text.strip()
        names = [line.strip() for line in text.split("\n") if line.strip()]
        if len(names) < 2:
            self.notify("Need at least 2 players", severity="error")
            return
        players = []
        for name in names:
            try:
                players.append(Player(name))
            except TournamentError as e:
                self.notify(str(e), severity="error")
                return
        t = Tournament("User Tournament", players, t_type=t_type)
        t.save_to_file(SAVE_FILE)
        self.dismiss(t)


class ConfirmDialog(ModalScreen):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def compose(self):
        yield Static(self.message)
        with Horizontal():
            yield Button("Yes", variant="primary", id="yes")
            yield Button("No", variant="default", id="no")

    def on_button_pressed(self, event):
        self.dismiss(event.button.id == "yes")

    def key_y(self):
        self.dismiss(True)

    def key_n(self):
        self.dismiss(False)

    def key_escape(self):
        self.dismiss(False)


class FileInputDialog(ModalScreen):
    def __init__(self, title: str, default: str = PLAYER_FILE):
        super().__init__()
        self._title = title
        self._default = default

    def compose(self):
        yield Static(self._title)
        yield Input(value=self._default, placeholder="filename")
        with Horizontal():
            yield Button("OK", variant="primary", id="ok")
            yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event):
        if event.button.id == "ok":
            self._submit()
        elif event.button.id == "cancel":
            self.dismiss(None)

    def on_input_submitted(self):
        self._submit()

    def _submit(self):
        name = self.query_one(Input).value.strip()
        if name:
            self.dismiss(name)


class RoundReviewScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("b", "dismiss", "Back"),
    ]

    def __init__(self, tournament):
        super().__init__()
        self.tournament = tournament

    def compose(self):
        with Horizontal():
            with Vertical(classes="panel"):
                yield Static("Rounds", classes="panel-title")
                yield DataTable(id="rounds-table", cursor_type="row")
            with Vertical(classes="panel"):
                yield Static("Boards", classes="panel-title")
                yield DataTable(id="detail-table")
        yield Footer()

    def on_mount(self):
        t = self.query_one("#rounds-table", DataTable)
        t.add_columns("Round", "Status")
        for i, rnd in enumerate(self.tournament.rounds, 1):
            if all(m.result is not None for m in rnd):
                status = "Complete"
            elif any(m.result is not None for m in rnd):
                status = "In Progress"
            else:
                status = "Pending"
            t.add_row(f"Round {i}", status)

    def action_dismiss(self):
        self.dismiss()

    def on_data_table_row_selected(self, event):
        if event.row_key is None:
            return
        table = self.query_one("#rounds-table", DataTable)
        row = table.get_row(event.row_key)
        rnd_num = int(row[0].split()[-1]) - 1
        dt = self.query_one("#detail-table", DataTable)
        dt.clear(columns=True)
        dt.add_columns("#", "White", "Black", "Result", "Time")
        rnd = self.tournament.rounds[rnd_num]
        for i, m in enumerate(rnd, 1):
            if m.is_bye:
                name = (m.white or m.black).name
                res = m.result.value if m.result else "AUTO"
                dt.add_row(str(i), name, "[BYE]", res, m.timestamp or "")
            else:
                res = m.result.value if m.result else "PENDING"
                dt.add_row(str(i), m.white.name, m.black.name, res, m.timestamp or "")


class ChessApp(App):
    CSS = CSS

    BINDINGS = [
        Binding("n", "next_or_cancel", "Next round"),
        Binding("a", "add_player", "Add player"),
        Binding("i", "import_players", "Import players"),
        Binding("p", "export_players_list", "Export players"),
        Binding("u", "undo", "Undo"),
        Binding("z", "snapshot", "Snapshot"),
        Binding("e", "export", "Export"),
        Binding("s", "save", "Save"),
        Binding("r", "review", "Review"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.tournament = None
        self.undo_stack = []
        self.result_mode = False

    def compose(self):
        with Vertical(classes="panel", id="standings-panel"):
            yield Static("Standings", classes="panel-title")
            yield DataTable(id="standings-table", cursor_type="row")
        with Vertical(classes="panel", id="round-panel"):
            yield Static("Round 0", classes="panel-title", id="round-title")
            yield DataTable(id="boards-table", cursor_type="row")
        yield Footer()

    def on_mount(self):
        if os.path.exists(SAVE_FILE):
            try:
                t = Tournament.load_from_file(SAVE_FILE)
                if t and len(t.players) >= 2:
                    self.tournament = t
            except Exception:
                pass
        if self.tournament:
            self._init_display()
        else:
            self.push_screen(SetupScreen(), self._on_setup_done)

    def _on_setup_done(self, result):
        if isinstance(result, Tournament):
            self.tournament = result
            self._init_display()
        else:
            self.exit()

    def _init_display(self):
        st = self.query_one("#standings-table", DataTable)
        st.clear(columns=True)
        st.add_columns("Pos", "Name", "Score", "BH")
        bt = self.query_one("#boards-table", DataTable)
        bt.clear(columns=True)
        bt.add_columns("#", "White", "Black", "Result")
        self._redraw()

    def _redraw(self):
        if not self.tournament:
            return
        st = self.query_one("#standings-table", DataTable)
        st.clear()
        for i, p in enumerate(self.tournament.get_standings(), 1):
            tag = " (wd)" if not p.active else ""
            st.add_row(str(i), p.name + tag, f"{p.score:.1f}", f"{p.buchholz:.1f}")

        bt = self.query_one("#boards-table", DataTable)
        bt.clear()
        if self.tournament.rounds:
            rnd = self.tournament.rounds[-1]
            pending = sum(1 for m in rnd if not m.is_bye and m.result is None)
            title = f"Round {self.tournament.current_round_num}"
            if pending and self.result_mode:
                title += f" [{pending} pending]"
            self.query_one("#round-title", Static).update(title)
            for i, m in enumerate(rnd, 1):
                if not m.is_bye:
                    bt.add_row(str(i), m.white.name, m.black.name, m.result.value if m.result else "PENDING")
            for i, m in enumerate(rnd, 1):
                if m.is_bye:
                    bt.add_row(str(i), (m.white or m.black).name, "[BYE]", m.result.value if m.result else "AUTO")
        else:
            self.query_one("#round-title", Static).update("Round 0")
        if self.result_mode and self.tournament and self.tournament.rounds:
            rnd = self.tournament.rounds[-1]
            for i, m in enumerate(rnd):
                if not m.is_bye and m.result is None:
                    self._focus(i + 1)
                    break
        else:
            try:
                bt.move_cursor(row=0, column=0)
            except RowDoesNotExist:
                pass

    def _record(self, code):
        if not self.result_mode or not self.tournament:
            return
        bt = self.query_one("#boards-table", DataTable)
        if bt.cursor_row is None or bt.cursor_row >= bt.row_count:
            return
        try:
            data = bt.get_row_at(bt.cursor_row)
        except Exception:
            return
        if data[3] != "PENDING":
            self.notify(f"Row {data[0]} is not pending")
            return
        rnd = self.tournament.rounds[-1]
        match = rnd[int(data[0]) - 1]
        if match.is_bye:
            return
        try:
            self.tournament.record_match_result(match, code)
            self.undo_stack.append(match)
            self.tournament.save_to_file(SAVE_FILE)
            self._redraw()
            rnd = self.tournament.rounds[-1]
            pending = [m for m in rnd if not m.is_bye and m.result is None]
            if pending:
                for i, m in enumerate(rnd):
                    if not m.is_bye and m.result is None:
                        self._focus(i + 1)
                        break
                self.notify(f"Recorded. {len(pending)} pending")
            else:
                self.result_mode = False
                self.notify("Round complete! Press N for next")
        except TournamentError as e:
            self.notify(str(e))

    def _focus(self, board_num):
        bt = self.query_one("#boards-table", DataTable)
        for i in range(bt.row_count):
            try:
                d = bt.get_row_at(i)
                if int(d[0]) == board_num:
                    bt.move_cursor(row=i, column=0)
                    return
            except Exception:
                pass

    def key_1(self):
        self._record("1-0")
    def key_w(self):
        if self.result_mode:
            self._record("1-0")
        else:
            self.action_withdraw()
    def key_2(self):
        self._record("0-1")
    def key_b(self):
        self._record("0-1")
    def key_3(self):
        self._record("1/2-1/2")
    def key_d(self):
        if self.result_mode:
            self._record("1/2-1/2")
        else:
            self.action_delete_round()
    def key_h(self):
        self._record("1/2-1/2")
    def key_escape(self):
        if self.result_mode:
            self.result_mode = False
            self.notify("Cancelled")
        self.query_one("#boards-table", DataTable).focus()

    def action_next_or_cancel(self):
        if not self.tournament:
            return
        if self.result_mode:
            self.result_mode = False
            self.notify("Cancelled")
            return
        if self.tournament.rounds and any(
            m.result is None for m in self.tournament.rounds[-1]
        ):
            self.result_mode = True
            rnd = self.tournament.rounds[-1]
            pending = [m for m in rnd if not m.is_bye and m.result is None]
            self.query_one("#boards-table", DataTable).focus()
            for i, m in enumerate(rnd):
                if not m.is_bye and m.result is None:
                    self._focus(i + 1)
                    break
            self.notify(f"Enter results | {len(pending)} pending | 1=W 2=B 3=D | Esc=cancel")
            return
        try:
            pairings = self.tournament.generate_next_round()
            self.undo_stack.clear()
            self.tournament.save_to_file(SAVE_FILE)
            self._redraw()
            for m in pairings:
                if m.is_bye:
                    self.tournament.record_match_result(m, "1-0")
            self.tournament.save_to_file(SAVE_FILE)
            self._redraw()
            pending = [m for m in pairings if not m.is_bye]
            if pending:
                self.result_mode = True
                self.query_one("#boards-table", DataTable).focus()
                for i, m in enumerate(pairings):
                    if not m.is_bye and m.result is None:
                        self._focus(i + 1)
                        break
                self.notify(f"Enter results | {len(pending)} pending | 1=W 2=B 3=D | Esc=cancel")
            else:
                self.notify("Round generated (all byes)")
        except TournamentError as e:
            self.notify(str(e))

    def action_add_player(self):
        if not self.tournament:
            return
        def cb(name):
            if name:
                try:
                    self.tournament.add_player(Player(name))
                    self.tournament.save_to_file(SAVE_FILE)
                    self._redraw()
                    self.notify(f"Added {name}")
                except TournamentError as e:
                    self.notify(str(e))
        self.push_screen(AddPlayerDialog(), cb)

    def action_import_players(self):
        if not self.tournament:
            return
        def cb(path):
            if not path:
                return
            try:
                with open(path) as f:
                    names = [l.strip() for l in f if l.strip()]
                count = 0
                for name in names:
                    try:
                        self.tournament.add_player(Player(name))
                        count += 1
                    except TournamentError:
                        self.notify(f"Skipped invalid name: {name}", severity="error")
                if count:
                    self.tournament.save_to_file(SAVE_FILE)
                    self._redraw()
                    self.notify(f"Imported {count} players")
            except FileNotFoundError:
                self.notify(f"File not found: {path}", severity="error")
            except Exception as e:
                self.notify(str(e), severity="error")
        self.push_screen(FileInputDialog("Import players from:", PLAYER_FILE), cb)

    def action_export_players_list(self):
        if not self.tournament:
            return
        def cb(path):
            if not path:
                return
            try:
                names = [p.name for p in self.tournament.players]
                with open(path, "w") as f:
                    f.write("\n".join(names) + "\n")
                self.notify(f"Exported {len(names)} players to {path}")
            except Exception as e:
                self.notify(str(e), severity="error")
        self.push_screen(FileInputDialog("Export players to:", PLAYER_FILE), cb)

    def action_withdraw(self):
        if not self.tournament:
            return
        def cb(player):
            if player:
                player.active = False
                self.tournament.save_to_file(SAVE_FILE)
                self._redraw()
                self.notify(f"Withdrew {player.name}")
        self.push_screen(WithdrawDialog(self.tournament.players), cb)

    def action_undo(self):
        if not self.undo_stack or not self.tournament:
            self.notify("Nothing to undo")
            return
        m = self.undo_stack.pop()
        m.result = None
        self.tournament.recalculate_state()
        self.tournament.save_to_file(SAVE_FILE)
        self._redraw()
        if self.tournament.rounds:
            rnd = self.tournament.rounds[-1]
            pending = [ma for ma in rnd if not ma.is_bye and ma.result is None]
            if pending:
                self.result_mode = True
                for i, ma in enumerate(rnd):
                    if not ma.is_bye and ma.result is None:
                        self._focus(i + 1)
                        break
        self.notify("Undone")

    def action_delete_round(self):
        if not self.tournament or not self.tournament.rounds:
            self.notify("No rounds to delete")
            return
        def cb(confirmed):
            if confirmed:
                self.tournament.delete_last_round()
                self.tournament.save_to_file(SAVE_FILE)
                self._redraw()
                self.notify("Round deleted")
        self.push_screen(ConfirmDialog("Delete last round?"), cb)

    def action_snapshot(self):
        if not self.tournament:
            return
        self.tournament.create_snapshot(SAVE_FILE)
        self.notify("Snapshot created")

    def action_export(self):
        if not self.tournament:
            return
        try:
            self.tournament.export_csv(CSV_FILE)
            self.tournament.export_html(HTML_FILE)
            self.notify("Exported")
        except Exception as e:
            self.notify(f"Export failed: {e}")

    def action_save(self):
        if not self.tournament:
            return
        self.tournament.save_to_file(SAVE_FILE)
        self.notify(f"Saved at {datetime.now().strftime('%H:%M')}")

    def action_review(self):
        if not self.tournament or not self.tournament.rounds:
            self.notify("No rounds yet")
            return
        self.push_screen(RoundReviewScreen(self.tournament))

    def action_quit(self):
        def cb(confirmed):
            if confirmed and self.tournament:
                self.tournament.save_to_file(SAVE_FILE)
            self.exit()
        self.push_screen(ConfirmDialog("Save before quitting?"), cb)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ChessApp().run()


if __name__ == "__main__":
    main()
