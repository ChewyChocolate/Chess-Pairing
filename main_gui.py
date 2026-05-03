import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QHeaderView, QListWidget,
    QSpinBox, QInputDialog, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt

from player import Player
from tournament import Tournament, TournamentType
from match import Match, Result
from errors import TournamentError

DATA_DIR = "tournaments"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DEFAULT_SAVE = os.path.join(DATA_DIR, "tournament_data.json")


class Sidebar(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setFixedWidth(200)
        self.setObjectName("sidebar")

        # Sidebar Title
        title = QLabel("CHESS PAIR")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 18px; padding: 20px; color: palette(link);")
        self.layout.addWidget(title)

        # Nav Buttons
        self.btn_dashboard = QPushButton("Standings")
        self.btn_dashboard.setObjectName("nav_btn")
        self.btn_dashboard.clicked.connect(self.main_window.switch_to_dashboard)
        self.layout.addWidget(self.btn_dashboard)

        # Matches Button
        self.btn_rounds = QPushButton("Matches")
        self.btn_rounds.setObjectName("nav_btn")
        self.btn_rounds.clicked.connect(self.main_window.switch_to_rounds)
        self.layout.addWidget(self.btn_rounds)
        
        # Wall Chart Button
        self.btn_wall = QPushButton("Wall Chart")
        self.btn_wall.setObjectName("nav_btn")
        self.btn_wall.clicked.connect(self.main_window.switch_to_wall_chart)
        self.layout.addWidget(self.btn_wall)
        
        # History Button
        self.btn_history = QPushButton("Match Records")
        self.btn_history.setObjectName("nav_btn")
        self.btn_history.clicked.connect(self.main_window.show_match_history)
        self.layout.addWidget(self.btn_history)
        
        self.layout.addSpacing(20)
        
        # SEARCH SECTION
        search_lbl = QLabel("QUICK SEARCH")
        search_lbl.setStyleSheet("font-size: 8pt; font-weight: bold; color: palette(window-text); padding: 0 20px; opacity: 0.6;")
        self.layout.addWidget(search_lbl)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find player...")
        self.search_input.setStyleSheet("margin: 5px 15px; padding: 8px; border-radius: 6px;")
        self.search_input.textChanged.connect(self.main_window.apply_filter)
        self.layout.addWidget(self.search_input)

        self.layout.addStretch()

        # Exit/New button
        self.btn_setup = QPushButton("Exit Tournament")
        self.btn_setup.setObjectName("nav_btn")
        self.btn_setup.setStyleSheet("color: #d32f2f;")
        self.btn_setup.clicked.connect(self.main_window.switch_to_setup)
        self.layout.addWidget(self.btn_setup)

        self.setLayout(self.layout)
        self.hide() # Hidden by default until tournament starts


class SetupView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Chess Tournament Pairing System")
        title.setObjectName("title")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Load Existing Option
        last_save = DEFAULT_SAVE
        if os.path.exists(last_save):
            self.load_btn = QPushButton(f"Quick Load Last ({os.path.basename(last_save)})")
            self.load_btn.clicked.connect(lambda: self.load_tournament(last_save))
            self.load_btn.setStyleSheet("padding: 10px; font-size: 16px;")
            layout.addWidget(self.load_btn)
            
            self.backup_btn = QPushButton("Browse Tournaments (.json)")
            self.backup_btn.clicked.connect(self.load_backup)
            self.backup_btn.setStyleSheet("padding: 8px; font-size: 14px; background-color: rgba(128,128,128,0.1);")
            layout.addWidget(self.backup_btn)

            lbl = QLabel("OR")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)

        # New Tournament Section
        new_label = QLabel("Create New Tournament")
        new_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(new_label)

        # Tournament Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Tournament Name:"))
        self.t_name_input = QLineEdit()
        self.t_name_input.setPlaceholderText("e.g. Blitz_Championship_2024")
        name_layout.addWidget(self.t_name_input)
        layout.addLayout(name_layout)

        # Format Selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem(TournamentType.SWISS.value, TournamentType.SWISS)
        self.format_combo.addItem(TournamentType.ROUND_ROBIN.value, TournamentType.ROUND_ROBIN)
        self.format_combo.currentIndexChanged.connect(self.toggle_rounds_input)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Rounds Input (for Swiss)
        self.rounds_layout = QHBoxLayout()
        self.rounds_layout.addWidget(QLabel("Rounds (0 for Auto):"))
        self.rounds_spinbox = QSpinBox()
        self.rounds_spinbox.setMinimum(0)
        self.rounds_spinbox.setMaximum(50)
        self.rounds_spinbox.setValue(0)
        self.rounds_layout.addWidget(self.rounds_spinbox)
        layout.addLayout(self.rounds_layout)

        # Players List
        layout.addWidget(QLabel("Players:"))
        self.player_list_widget = QListWidget()
        layout.addWidget(self.player_list_widget)

        # Add Player Input
        add_player_layout = QHBoxLayout()
        self.player_input = QLineEdit()
        self.player_input.setPlaceholderText("Enter player name...")
        self.player_input.returnPressed.connect(self.add_player)
        add_player_layout.addWidget(self.player_input)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_player)
        add_player_layout.addWidget(add_btn)
        layout.addLayout(add_player_layout)
        
        remove_btn = QPushButton("Remove Selected Player")
        remove_btn.clicked.connect(self.remove_player)
        layout.addWidget(remove_btn)

        # Start Button
        self.start_btn = QPushButton("Start Tournament")
        self.start_btn.setObjectName("primary_btn")
        self.start_btn.setStyleSheet("padding: 10px; font-size: 16px; font-weight: bold; background-color: #2E7D32; color: white; border: none;")
        self.start_btn.clicked.connect(self.start_tournament)
        layout.addWidget(self.start_btn)

        self.setLayout(layout)

    def toggle_rounds_input(self):
        t_type = self.format_combo.currentData()
        is_swiss = t_type == TournamentType.SWISS
        for i in range(self.rounds_layout.count()):
            widget = self.rounds_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(is_swiss)

    def add_player(self):
        name = self.player_input.text().strip()
        if name:
            # Check for duplicates in UI
            items = [self.player_list_widget.item(i).text() for i in range(self.player_list_widget.count())]
            if name in items:
                QMessageBox.warning(self, "Error", "Player already in list.")
                return
            self.player_list_widget.addItem(name)
            self.player_input.clear()

    def remove_player(self):
        selected = self.player_list_widget.selectedItems()
        if not selected:
            return
        for item in selected:
            self.player_list_widget.takeItem(self.player_list_widget.row(item))

    def start_tournament(self):
        t_name = self.t_name_input.text().strip()
        if not t_name:
            QMessageBox.warning(self, "Error", "Please enter a tournament name.")
            return

        if self.player_list_widget.count() < 2:
            QMessageBox.warning(self, "Error", "You need at least 2 players to start a tournament.")
            return

        players = []
        for i in range(self.player_list_widget.count()):
            name = self.player_list_widget.item(i).text()
            players.append(Player(name))

        t_type = self.format_combo.currentData()
        rounds_val = self.rounds_spinbox.value()
        total_rounds = rounds_val if rounds_val > 0 else None

        try:
            filename = f"{t_name}.json"
            save_path = os.path.join(DATA_DIR, filename)
            
            t = Tournament(t_name, players, t_type=t_type, total_rounds=total_rounds)
            t.save_to_file(save_path)
            t.create_snapshot(save_path)
            
            self.main_window.current_save_path = save_path
            self.main_window.set_tournament(t)
            self.main_window.switch_to_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start tournament: {e}")

    def load_tournament(self, path=DEFAULT_SAVE):
        try:
            t = Tournament.load_from_file(path)
            self.main_window.current_save_path = path
            self.main_window.set_tournament(t)
            self.main_window.switch_to_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def load_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Restore Tournament Backup", DATA_DIR, "Tournament Files (*.json)")
        if file_path:
            try:
                t = Tournament.load_from_file(file_path)
                # Ensure snapshots work from the correct base
                main_path = os.path.join(DATA_DIR, f"{t.name}.json")
                t.save_to_file(main_path)
                
                self.main_window.current_save_path = main_path
                self.main_window.set_tournament(t)
                self.main_window.switch_to_dashboard()
                QMessageBox.information(self, "Restored", f"Successfully restored '{t.name}' from backup.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to restore backup: {e}")


class DashboardView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        # Left side - Standings
        left_layout = QVBoxLayout()
        
        self.header_label = QLabel("Tournament: --")
        self.header_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        left_layout.addWidget(self.header_label)

        self.status_label = QLabel("Round -- of --")
        left_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Pos", "Name", "Rating", "Score", "SB", "BH"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.show_player_profile)
        left_layout.addWidget(self.table)

        layout.addLayout(left_layout, stretch=3)

        # Right side - Controls
        right_layout = QVBoxLayout()
        
        # Removed btn_rounds as it's now in the sidebar

        self.btn_add_player = QPushButton("Add Player")
        self.btn_add_player.clicked.connect(self.add_player)
        right_layout.addWidget(self.btn_add_player)

        self.btn_withdraw = QPushButton("Withdraw Player")
        self.btn_withdraw.clicked.connect(self.withdraw_player)
        right_layout.addWidget(self.btn_withdraw)
        
        self.btn_rating = QPushButton("Update Rating")
        self.btn_rating.clicked.connect(self.update_rating)
        right_layout.addWidget(self.btn_rating)

        right_layout.addStretch()

        self.btn_export = QPushButton("Export CSV/HTML")
        self.btn_export.clicked.connect(self.export_standings)
        right_layout.addWidget(self.btn_export)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_data)
        right_layout.addWidget(self.btn_save)

        self.btn_format = QPushButton("Change Format")
        self.btn_format.clicked.connect(self.change_format)
        right_layout.addWidget(self.btn_format)

        layout.addLayout(right_layout, stretch=1)

        self.setLayout(layout)

    def refresh(self):
        t = self.main_window.tournament
        if not t:
            return

        self.header_label.setText(f"Tournament: {t.name} ({t.t_type.value})")
        remaining = max(0, t.total_rounds - t.current_round_num) if t.total_rounds else "?"
        
        total_r = t.total_rounds if t.total_rounds else "?"
        self.status_label.setText(f"Round {t.current_round_num} of {total_r} ({remaining} remaining)")

        standings = t.get_standings()
        self.table.setRowCount(len(standings))

        # Tooltips for headers
        self.table.horizontalHeaderItem(3).setToolTip("Sonneborn-Berger: Sum of defeated opponents' scores plus half of drawn opponents' scores")
        self.table.horizontalHeaderItem(4).setToolTip("Buchholz: Sum of all opponents' scores")

        for i, p in enumerate(standings):
            status = "" if p.active else " (Withdrawn)"
            
            pos_item = QTableWidgetItem(str(i + 1))
            pos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.table.setItem(i, 0, pos_item)
            self.table.setItem(i, 1, QTableWidgetItem(p.name + status))
            self.table.setItem(i, 2, QTableWidgetItem(str(p.rating)))
            self.table.setItem(i, 3, QTableWidgetItem(f"{p.score:.1f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{p.sonneborn_berger:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{p.buchholz:.1f}"))
            
            # Leader Highlight (Position 1)
            if i == 0 and p.score > 0:
                for col in range(6):
                    item = self.table.item(i, col)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    
                    # Highlight background
                    if self.palette().window().color().lightness() > 128:
                        item.setBackground(Qt.GlobalColor.yellow if col == 0 else Qt.GlobalColor.transparent)
                    else:
                        item.setBackground(Qt.GlobalColor.darkYellow if col == 0 else Qt.GlobalColor.transparent)

            # Grey out withdrawn players
            if not p.active:
                for col in range(6):
                    item = self.table.item(i, col)
                    item.setForeground(Qt.GlobalColor.gray)
        # Disable format change if results exist
        can_change_format = t.current_round_num <= 1 and not (t.rounds and any(m.result is not None for m in t.rounds[0]))
        self.btn_format.setEnabled(can_change_format)
        
        # Re-apply current search if any
        self.filter_table(self.main_window.sidebar.search_input.text())

    def filter_table(self, text: str):
        text = text.lower()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            if name_item:
                match = text in name_item.text().lower()
                self.table.setRowHidden(row, not match)

    def show_player_profile(self, item):
        row = item.row()
        t = self.main_window.tournament
        standings = t.get_standings()
        
        # Check if row is visible (it might be hidden due to filter)
        # But even if filtered, standings index should match row index if we rebuild the whole table on refresh
        # Wait, if filtered some rows are hidden but the underlying items are still in the same order
        if 0 <= row < len(standings):
            p = standings[row]
            dialog = PlayerProfileDialog(p, t, self)
            dialog.exec()

    def add_player(self):
        name, ok = QInputDialog.getText(self, "Add Player", "Enter new player name:")
        if ok and name.strip():
            t = self.main_window.tournament
            try:
                t.add_player(Player(name.strip()))
                t.save_to_file(self.main_window.current_save_path)
                self.refresh()
                QMessageBox.information(self, "Success", f"Added {name} to the tournament.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def withdraw_player(self):
        t = self.main_window.tournament
        active_players = [p.name for p in t.players if p.active]
        if not active_players:
            QMessageBox.information(self, "Info", "No active players to withdraw.")
            return

        name, ok = QInputDialog.getItem(self, "Withdraw Player", "Select player to withdraw:", active_players, 0, False)
        if ok and name:
            for p in t.players:
                if p.name == name:
                    p.active = False
                    t.save_to_file(self.main_window.current_save_path)
                    self.refresh()
                    QMessageBox.information(self, "Success", f"{name} has been withdrawn.")
                    break

    def export_standings(self):
        t = self.main_window.tournament
        csv_file = "standings.csv"
        html_file = "standings.html"
        
        # Check if files exist and ask for confirmation
        files_exist = os.path.exists(csv_file) or os.path.exists(html_file)
        if files_exist:
            reply = QMessageBox.question(self, "Export", 
                                         "This will overwrite existing files. Continue?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            t.export_csv(csv_file)
            t.export_html(html_file)
            QMessageBox.information(self, "Success", f"Exported standings to {csv_file} and {html_file}")
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def save_data(self):
        try:
            self.main_window.tournament.save_to_file(self.main_window.current_save_path)
            QMessageBox.information(self, "Success", "Tournament saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
            
    def change_format(self):
        t = self.main_window.tournament
        new_type = TournamentType.ROUND_ROBIN if t.t_type == TournamentType.SWISS else TournamentType.SWISS
        
        reply = QMessageBox.question(self, "Change Format", 
                                     f"Switch from {t.t_type.value} to {new_type.value}?\nThis will reset current pairings.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            t.t_type = new_type
            t.rounds = []
            t.current_round_num = 0
            if hasattr(t, '_rr_schedule'):
                delattr(t, '_rr_schedule')
                
            if t.t_type == TournamentType.SWISS:
                 rounds_val, ok = QInputDialog.getInt(self, "Swiss Rounds", "Enter total rounds (0 for Auto):", 0, 0, 50)
                 if ok:
                     t.total_rounds = rounds_val if rounds_val > 0 else None
            
            t.save_to_file(self.main_window.current_save_path)
            self.refresh()

    def update_rating(self):
        items = self.table.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selection Required", "Select a player to update their rating.")
            return
            
        row = items[0].row()
        standings = self.main_window.tournament.get_standings()
        if 0 <= row < len(standings):
            p = standings[row]
            rating, ok = QInputDialog.getInt(self, "Update Rating", f"Enter new rating for {p.name}:", p.rating, 0, 3000)
            if ok:
                p.rating = rating
                self.main_window.tournament.recalculate_state() # Just in case R1 standings dependency
                self.main_window.tournament.save_to_file(self.main_window.current_save_path)
                self.refresh()

class RoundsView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        # Removed btn_back as it's now in the sidebar
        
        top_layout.addStretch()
        
        self.round_combo = QComboBox()
        self.round_combo.currentIndexChanged.connect(self.load_round)
        top_layout.addWidget(QLabel("Select Round:"))
        top_layout.addWidget(self.round_combo)
        
        layout.addLayout(top_layout)

        # Table for matches
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Board", "White", "Black", "Result Action"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(3, 220)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Bottom controls
        bottom_layout = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Next Round")
        self.btn_generate.setObjectName("primary_btn")
        self.btn_generate.setStyleSheet("padding: 10px; background-color: #1565C0; color: white; font-weight: bold; border: none;")
        self.btn_generate.clicked.connect(self.generate_next_round)
        bottom_layout.addWidget(self.btn_generate)
        
        self.btn_swap = QPushButton("Swap Players")
        self.btn_swap.clicked.connect(self.manual_swap_dialog)
        bottom_layout.addWidget(self.btn_swap)
        
        self.btn_panic = QPushButton("Delete Last Round")
        self.btn_panic.setStyleSheet("color: #C62828; font-weight: bold;")
        self.btn_panic.clicked.connect(self.delete_last_round)
        bottom_layout.addWidget(self.btn_panic)
        
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def refresh(self):
        t = self.main_window.tournament
        if not t:
            return

        # Update round combo
        self.round_combo.blockSignals(True)
        self.round_combo.clear()
        for i in range(len(t.rounds)):
            self.round_combo.addItem(f"Round {i+1}", i)
        
        if t.rounds:
            self.round_combo.setCurrentIndex(len(t.rounds) - 1)
        self.round_combo.blockSignals(False)
        
        self.load_round()
        self.update_generate_button()

    def update_generate_button(self):
        t = self.main_window.tournament
        if not t:
            return
            
        has_pending = False
        if t.rounds:
             last_round = t.rounds[-1]
             has_pending = any(m.result is None for m in last_round)
             
        # Disable generation if pending results
        is_over = t.total_rounds and t.current_round_num >= t.total_rounds

        if is_over and not has_pending:
            self.btn_generate.setText("★ SHOW WINNERS & COMPLETE ★")
            self.btn_generate.setEnabled(True)
            self.btn_generate.setStyleSheet("padding: 12px; background-color: #FFD700; color: #333; font-weight: bold; border-radius: 8px;")
            try: self.btn_generate.clicked.disconnect()
            except: pass
            self.btn_generate.clicked.connect(self.show_winners)
        elif is_over and has_pending:
            self.btn_generate.setText("Record final results to see winners")
            self.btn_generate.setEnabled(False)
            self.btn_generate.setStyleSheet("padding: 10px; background-color: rgba(128,128,128,0.2); color: gray;")
        elif has_pending:
            self.btn_generate.setText("Enter all results to generate next round")
            self.btn_generate.setEnabled(False)
            self.btn_generate.setStyleSheet("padding: 10px; background-color: rgba(128,128,128,0.2); color: gray;")
        else:
            self.btn_generate.setText("Generate Next Round")
            self.btn_generate.setEnabled(True)
            self.btn_generate.setStyleSheet("padding: 10px; background-color: #1565C0; color: white; font-weight: bold;")
            try: self.btn_generate.clicked.disconnect()
            except: pass
            self.btn_generate.clicked.connect(self.generate_next_round)

    def load_round(self):
        t = self.main_window.tournament
        idx = self.round_combo.currentData()
        
        if idx is None or not t.rounds:
            self.table.setRowCount(0)
            return

        selected_round = t.rounds[idx]
        self.table.setRowCount(len(selected_round))

        for row, match in enumerate(selected_round):
            board_item = QTableWidgetItem(str(row + 1))
            board_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, board_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(match.white.name))
            
            if match.is_bye:
                self.table.setItem(row, 2, QTableWidgetItem("(BYE)"))
            else:
                self.table.setItem(row, 2, QTableWidgetItem(match.black.name))

            # Result Widget
            res_widget = QWidget()
            res_layout = QHBoxLayout(res_widget)
            res_layout.setContentsMargins(5, 2, 5, 2)

            if match.is_bye:
                if not match.result:
                    btn_bye = QPushButton("Record Bye")
                    btn_bye.clicked.connect(lambda checked, m=match: self.set_result(m, "1-0 (BYE)"))
                    res_layout.addWidget(btn_bye)
                else:
                    res_layout.addWidget(QLabel("1-0 (BYE)"))
            else:
                if match.result == Result.WHITE_WIN:
                    res_lbl = QLabel("White Wins (1-0)")
                    res_lbl.setStyleSheet("color: white; background-color: #2E7D32; padding: 2px 6px; border-radius: 4px; font-weight: bold;")
                    res_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    res_layout.addWidget(res_lbl)
                elif match.result == Result.BLACK_WIN:
                    res_lbl = QLabel("Black Wins (0-1)")
                    res_lbl.setStyleSheet("color: white; background-color: #C62828; padding: 2px 6px; border-radius: 4px; font-weight: bold;")
                    res_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    res_layout.addWidget(res_lbl)
                elif match.result == Result.DRAW:
                    res_lbl = QLabel("Draw (½-½)")
                    res_lbl.setStyleSheet("color: white; background-color: #757575; padding: 2px 6px; border-radius: 4px; font-weight: bold;")
                    res_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    res_layout.addWidget(res_lbl)
                else: # Pending result - QUICK BUTTONS
                    btn_w = QPushButton("1-0")
                    btn_w.setToolTip("White Wins")
                    btn_w.setFixedWidth(55)
                    btn_w.setStyleSheet("background-color: #2E7D32; color: white; border: none; font-weight: bold;")
                    btn_w.clicked.connect(lambda chk, m=match: self.set_result(m, "1-0"))
                    
                    btn_d = QPushButton("½-½")
                    btn_d.setToolTip("Draw")
                    btn_d.setFixedWidth(55)
                    btn_d.setStyleSheet("background-color: #757575; color: white; border: none; font-weight: bold;")
                    btn_d.clicked.connect(lambda chk, m=match: self.set_result(m, "1/2-1/2"))
                    
                    btn_b = QPushButton("0-1")
                    btn_b.setToolTip("Black Wins")
                    btn_b.setFixedWidth(55)
                    btn_b.setStyleSheet("background-color: #C62828; color: white; border: none; font-weight: bold;")
                    btn_b.clicked.connect(lambda chk, m=match: self.set_result(m, "0-1"))
                    
                    res_layout.addWidget(btn_w)
                    res_layout.addWidget(btn_d)
                    res_layout.addWidget(btn_b)

            if match.result is not None:
                # Add a reset button to go back to pending
                btn_reset = QPushButton("↺")
                btn_reset.setToolTip("Clear Result")
                btn_reset.setFixedWidth(30)
                btn_reset.setStyleSheet("background-color: transparent; border: 1px solid rgba(128,128,128,0.3); color: gray;")
                btn_reset.clicked.connect(lambda chk, m=match: self.set_result(m, "Pending"))
                res_layout.addWidget(btn_reset)

            self.table.setCellWidget(row, 3, res_widget)

    def set_result(self, match: Match, text: str):
        t = self.main_window.tournament
        
        try:
             if text == "Pending":
                  match.result = None
                  t.recalculate_state()
             else:
                  t.record_match_result(match, text)
             
             t.save_to_file(self.main_window.current_save_path)
             self.load_round()
             self.update_generate_button()
        except Exception as e:
             QMessageBox.critical(self, "Error", str(e))
             self.load_round() # Reset UI

    def generate_next_round(self):
        t = self.main_window.tournament
        try:
            t.generate_next_round()
            t.save_to_file(self.main_window.current_save_path)
            t.create_snapshot(self.main_window.current_save_path)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate round: {e}")

    def delete_last_round(self):
        t = self.main_window.tournament
        if not t or not t.rounds:
            return
            
        reply = QMessageBox.warning(self, "PANIC BUTTON", 
                                  f"Are you sure you want to PERMANENTLY delete Round {len(t.rounds)}?\nThis cannot be undone.",
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                t.delete_last_round()
                t.save_to_file(self.main_window.current_save_path)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete round: {e}")

    def show_winners(self):
        standings = self.main_window.tournament.get_standings()
        dialog = WinnersDialog(standings, self.main_window)
        dialog.exec()

    def manual_swap_dialog(self):
        t = self.main_window.tournament
        idx = self.round_combo.currentData()
        if idx is None or idx >= len(t.rounds):
            return
            
        # Check if results are already recorded
        if any(m.result is not None for m in t.rounds[idx]):
            QMessageBox.warning(self, "Cannot Swap", "Cannot swap players after results have been recorded for this round.")
            return

        # NEW: List all player names in this round
        players_in_round = {} # name -> Player object
        for match in t.rounds[idx]:
            if match.white: players_in_round[match.white.name] = match.white
            if match.black: players_in_round[match.black.name] = match.black
            
        names = sorted(list(players_in_round.keys()))
        if len(names) < 2:
            QMessageBox.information(self, "N/A", "Need at least 2 players in this round to perform a swap.")
            return
            
        name1, ok1 = QInputDialog.getItem(self, "Swap Players", "Select first player:", names, 0, False)
        if not ok1: return
        
        name2, ok2 = QInputDialog.getItem(self, "Swap Players", f"Swap {name1} with:", [n for n in names if n != name1], 0, False)
        if not ok2: return
        
        try:
            t.swap_players(idx, players_in_round[name1], players_in_round[name2])
            t.save_to_file(self.main_window.current_save_path)
            self.refresh()
            QMessageBox.information(self, "Success", f"Swapped {name1} and {name2} successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Swap failed: {e}")


class PlayerProfileDialog(QDialog):
    def __init__(self, player, tournament, parent=None):
        super().__init__(parent)
        self.player = player
        self.tournament = tournament
        self.setWindowTitle(f"Player Profile - {player.name}")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary Header
        header = QLabel(f"{self.player.name}")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; color: palette(link);")
        layout.addWidget(header)
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Score: <b>{self.player.score:.1f}</b>"))
        info_layout.addWidget(QLabel(f"SB: {self.player.sonneborn_berger:.2f}"))
        info_layout.addWidget(QLabel(f"BH: {self.player.buchholz:.1f}"))
        layout.addLayout(info_layout)
        
        layout.addSpacing(15)
        layout.addWidget(QLabel("<b>Round History:</b>"))
        
        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Round", "Color", "Opponent", "Result"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        history = []
        for r_idx, rnd in enumerate(self.tournament.rounds):
            match_found = None
            for match in rnd:
                if match.white == self.player:
                    match_found = (r_idx + 1, "White", match.black.name if match.black else "(BYE)", match.result)
                    break
                elif match.black == self.player:
                    match_found = (r_idx + 1, "Black", match.white.name if match.white else "(BYE)", match.result)
                    break
            
            if match_found:
                history.append(match_found)
        
        self.table.setRowCount(len(history))
        for i, (r_num, col, opp, res) in enumerate(history):
            self.table.setItem(i, 0, QTableWidgetItem(str(r_num)))
            self.table.setItem(i, 1, QTableWidgetItem(col))
            self.table.setItem(i, 2, QTableWidgetItem(opp))
            
            res_str = "--"
            if res:
                if (col == "White" and res == Result.WHITE_WIN) or (col == "Black" and res == Result.BLACK_WIN) or res == Result.BYE:
                    res_str = "Win (1)"
                elif res == Result.DRAW:
                    res_str = "Draw (½)"
                else:
                    res_str = "Loss (0)"
            
            res_item = QTableWidgetItem(res_str)
            if "Win" in res_str: res_item.setForeground(Qt.GlobalColor.darkGreen)
            if "Loss" in res_str: res_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(i, 3, res_item)
            
        layout.addWidget(self.table)
        
        # Close Button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


class WinnersDialog(QDialog):
    def __init__(self, standings, parent=None):
        super().__init__(parent)
        self.standings = standings
        self.setWindowTitle("Tournament Complete - Winners Ceremony")
        self.setMinimumWidth(450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        # Trophy/Icon if we had one
        title = QLabel("★ TOURNAMENT CHAMPIONS ★")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22pt; font-weight: bold; color: #FFD700; margin-bottom: 5px;")
        layout.addWidget(title)

        if len(self.standings) >= 1:
            self.add_winner_row(layout, "1st PLACE", self.standings[0], "font-size: 18pt; font-weight: bold; background: rgba(255, 215, 0, 0.15); border-radius: 10px; padding: 15px;")
        
        if len(self.standings) >= 2:
            self.add_winner_row(layout, "2nd PLACE", self.standings[1], "font-size: 14pt; background: rgba(192, 192, 192, 0.1); border-radius: 8px; padding: 10px;")
            
        if len(self.standings) >= 3:
            self.add_winner_row(layout, "3rd PLACE", self.standings[2], "font-size: 13pt; background: rgba(205, 127, 50, 0.05); border-radius: 8px; padding: 10px;")

        layout.addSpacing(20)
        
        btn_done = QPushButton("Return to Tournament Home")
        btn_done.setStyleSheet("padding: 10px; background-color: palette(link); color: white; border: none; font-weight: bold;")
        btn_done.clicked.connect(self.finish)
        layout.addWidget(btn_done)

    def add_winner_row(self, layout, title_text, player, style_qss):
        widget = QWidget()
        widget.setStyleSheet(style_qss)
        inner_layout = QHBoxLayout(widget)
        
        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet("font-weight: bold; color: palette(link);")
        inner_layout.addWidget(lbl_title)
        
        inner_layout.addStretch()
        
        lbl_name = QLabel(player.name)
        lbl_name.setStyleSheet("font-weight: bold;")
        inner_layout.addWidget(lbl_name)
        
        lbl_score = QLabel(f"Score: {player.score:.1f}")
        lbl_score.setStyleSheet("opacity: 0.8;")
        inner_layout.addWidget(lbl_score)
        
        layout.addWidget(widget)

    def finish(self):
        self.accept()
        # Navigate to Dashboard to show final stands
        if isinstance(self.parent(), QMainWindow) or (hasattr(self.parent(), "main_window")):
            main_win = self.parent() if hasattr(self.parent(), "switch_to_dashboard") else self.parent().main_window
            main_win.switch_to_dashboard()


class MatchHistoryDialog(QDialog):
    def __init__(self, tournament, parent=None):
        super().__init__(parent)
        self.tournament = tournament
        self.setWindowTitle("Match Records & Activity Log")
        self.resize(700, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("Tournament Match Activity")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: palette(link);")
        layout.addWidget(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Round/Board", "White", "Black", "Result"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Collect all matches with results
        logs = []
        for r_idx, rnd in enumerate(self.tournament.rounds):
            for b_idx, match in enumerate(rnd):
                if match.result or match.timestamp:
                    logs.append({
                        "time": match.timestamp or "--:--:--",
                        "rb": f"R{r_idx+1} Board {b_idx+1}",
                        "white": match.white.name if match.white else "(BYE)",
                        "black": match.black.name if match.black else "(BYE)",
                        "res": match.result.value if match.result else "Pending"
                    })
        
        # Sort logs by timestamp (newest first)
        logs.sort(key=lambda x: x["time"], reverse=True)
        
        self.table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.table.setItem(i, 0, QTableWidgetItem(log["time"]))
            self.table.setItem(i, 1, QTableWidgetItem(log["rb"]))
            self.table.setItem(i, 2, QTableWidgetItem(log["white"]))
            self.table.setItem(i, 3, QTableWidgetItem(log["black"]))
            
            res_item = QTableWidgetItem(log["res"])
            if log["res"] == "1-0": res_item.setForeground(Qt.GlobalColor.darkGreen)
            if log["res"] == "0-1": res_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(i, 4, res_item)
            
        layout.addWidget(self.table)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


class WallChartView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 20)

        header_layout = QHBoxLayout()
        title = QLabel("Tournament Wall Chart")
        title.setObjectName("title")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 5px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        info_label = QLabel("Notation: [Opp-Rank][Color][Result]")
        info_label.setStyleSheet("font-style: italic; color: palette(window-text); opacity: 0.7;")
        header_layout.addWidget(info_label)
        
        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def refresh(self):
        t = self.main_window.tournament
        if not t:
            return

        standings = t.get_standings()
        num_rounds = len(t.rounds)
        
        # Create mapping of Player object to its current rank (1..N)
        player_ranks = {p.id: i + 1 for i, p in enumerate(standings)}

        self.table.setColumnCount(4 + num_rounds)
        headers = ["Rank", "Name"] + [f"R{i+1}" for i in range(num_rounds)] + ["Pts", "SB"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(standings))
        
        # Configure columns
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for r_idx in range(num_rounds):
            self.table.horizontalHeader().setSectionResizeMode(2 + r_idx, QHeaderView.ResizeMode.ResizeToContents)

        for i, p in enumerate(standings):
            # Rank & Name
            rank_item = QTableWidgetItem(str(i + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, rank_item)
            
            name_status = p.name + ("" if p.active else " (W)")
            self.table.setItem(i, 1, QTableWidgetItem(name_status))
            
            # For each round
            for r_idx in range(num_rounds):
                match_info = "--"
                for match in t.rounds[r_idx]:
                    if match.white == p:
                        if match.is_bye:
                            match_info = "BYE"
                        elif match.black:
                            opp_rank = player_ranks.get(match.black.id, "?")
                            res_val = "?"
                            if match.result == Result.WHITE_WIN: res_val = "1"
                            elif match.result == Result.BLACK_WIN: res_val = "0"
                            elif match.result == Result.DRAW: res_val = "½"
                            match_info = f"{opp_rank}w{res_val}"
                        break
                    elif match.black == p:
                        if match.white:
                            opp_rank = player_ranks.get(match.white.id, "?")
                            res_val = "?"
                            if match.result == Result.BLACK_WIN: res_val = "1"
                            elif match.result == Result.WHITE_WIN: res_val = "0"
                            elif match.result == Result.DRAW: res_val = "½"
                            match_info = f"{opp_rank}b{res_val}"
                        break
                
                item = QTableWidgetItem(match_info)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Visual hints for win/loss/draw
                if "1" in match_info:
                    item.setForeground(QApplication.palette().link())
                elif ("0" in match_info and "w" in match_info) or ("0" in match_info and "b" in match_info):
                    item.setForeground(Qt.GlobalColor.red)
                    
                self.table.setItem(i, 2 + r_idx, item)
            
            # Points & SB
            pts_item = QTableWidgetItem(f"{p.score:.1f}")
            pts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pts_item.setFont(rank_item.font())
            self.table.setItem(i, 2 + num_rounds, pts_item)
            
            sb_item = QTableWidgetItem(f"{p.sonneborn_berger:.1f}")
            sb_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3 + num_rounds, sb_item)
            
        # Re-apply current search if any
        self.filter_table(self.main_window.sidebar.search_input.text())

    def filter_table(self, text: str):
        text = text.lower()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            if name_item:
                match = text in name_item.text().lower()
                self.table.setRowHidden(row, not match)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tournament: Tournament = None
        self.current_save_path: str = DEFAULT_SAVE
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Chess Pairing application")
        self.resize(1000, 700)

        # Central Widget Layout
        central_widget = QWidget()
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar(self)
        self.main_layout.addWidget(self.sidebar)

        # Right-side Main Content area
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Progress Bar section
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(20, 15, 20, 5)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(128, 128, 128, 0.1);
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: palette(link);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Tournament Progress: 0%")
        self.progress_label.setStyleSheet("font-size: 9pt; color: palette(link); margin-bottom: 5px;")
        progress_layout.addWidget(self.progress_label)
        
        content_layout.addWidget(self.progress_container)
        self.progress_container.hide() # Hidden at start

        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        self.setup_view = SetupView(self)
        self.dashboard_view = DashboardView(self)
        self.rounds_view = RoundsView(self)
        self.wall_chart_view = WallChartView(self)
        
        self.stacked_widget.addWidget(self.setup_view)
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.rounds_view)
        self.stacked_widget.addWidget(self.wall_chart_view)

        self.main_layout.addWidget(content_container)
        self.setCentralWidget(central_widget)
        
    def set_tournament(self, t: Tournament):
        self.tournament = t
        self.sidebar.show()
        self.progress_container.show()
        self.update_progress()

    def update_progress(self):
        if not self.tournament or not self.tournament.total_rounds:
            self.progress_bar.setValue(0)
            self.progress_label.setText("Tournament Progress: --")
            return
            
        current = self.tournament.current_round_num
        total = self.tournament.total_rounds
        progress = int((current / total) * 100)
        
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Tournament Progress: {progress}% (Round {current} of {total})")

    def switch_to_setup(self):
        reply = QMessageBox.question(self, "Exit", "Return to setup screen? Unsaved progress will be lost.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.tournament = None
            self.sidebar.hide()
            self.progress_container.hide()
            self.stacked_widget.setCurrentWidget(self.setup_view)

    def switch_to_dashboard(self):
        self.update_progress()
        self.dashboard_view.refresh()
        self.stacked_widget.setCurrentWidget(self.dashboard_view)

    def switch_to_rounds(self):
        self.update_progress()
        self.rounds_view.refresh()
        self.stacked_widget.setCurrentWidget(self.rounds_view)

    def switch_to_wall_chart(self):
        self.sidebar.search_input.clear() # Clear filter when switching
        self.update_progress()
        self.wall_chart_view.refresh()
        self.stacked_widget.setCurrentWidget(self.wall_chart_view)

    def show_match_history(self):
        if not self.tournament:
            return
        dialog = MatchHistoryDialog(self.tournament, self)
        dialog.exec()
        
    def apply_filter(self, text: str):
        active_view = self.stacked_widget.currentWidget()
        if hasattr(active_view, "filter_table"):
            active_view.filter_table(text)


def main():
    app = QApplication(sys.argv)
    
    # Global stylesheet for better look and theme compatibility
    app.setStyleSheet("""
        * {
            font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', 'Arial', sans-serif;
            font-size: 10pt;
        }
        QMainWindow {
            background-color: palette(window);
        }
        QWidget {
            color: palette(window-text);
        }
        QPushButton {
            border: 1px solid rgba(128, 128, 128, 0.4);
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: rgba(128, 128, 128, 0.2);
            border-color: palette(link);
        }
        QPushButton:pressed {
            background-color: rgba(128, 128, 128, 0.4);
        }
        QTableWidget {
            gridline-color: rgba(128, 128, 128, 0.3);
            alternate-background-color: rgba(128, 128, 128, 0.05);
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 8px;
            background-color: palette(base);
        }
        QHeaderView::section {
            background-color: rgba(128, 128, 128, 0.15);
            color: palette(window-text);
            padding: 8px;
            border: none;
            border-bottom: 2px solid palette(link);
            font-weight: bold;
        }
        QLineEdit, QComboBox, QSpinBox, QListWidget {
            background-color: palette(base);
            border: 1px solid rgba(128, 128, 128, 0.4);
            border-radius: 4px;
            padding: 5px;
            color: palette(text);
        }
        QLineEdit:focus, QComboBox:focus {
            border-color: palette(link);
        }
        QLabel#title {
            color: palette(link);
            font-size: 20pt;
        }
        QWidget#sidebar {
            background-color: rgba(0, 0, 0, 0.05);
            border-right: 1px solid rgba(128, 128, 128, 0.3);
        }
        QPushButton#nav_btn {
            border: none;
            border-radius: 0;
            padding: 18px 25px;
            text-align: left;
            font-size: 11pt;
            background-color: transparent;
            font-weight: 400;
        }
        QPushButton#nav_btn:hover {
            background-color: rgba(128, 128, 128, 0.15);
        }
        QPushButton#nav_btn:pressed {
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }
        QPushButton#primary_btn {
           background-color: palette(link);
           color: white;
           border-radius: 8px;
           font-size: 11pt;
           border: none;
        }
        QPushButton#primary_btn:hover {
           background-color: palette(link);
           border: 1px solid white;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
