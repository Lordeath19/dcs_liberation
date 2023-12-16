from typing import Set

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QScrollArea,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLayout,
    QLabel,
    QSizePolicy,
    QPushButton,
    QSpacerItem,
)

from game.dcs.aircrafttype import AircraftType
from game.procurement import ProcurementAi
from game.squadrons import Squadron
from qt_ui.models import GameModel
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.QUnitInfoWindow import QUnitInfoWindow


class BuyQuotasDialog(QDialog):
    """Dialog window showing all scheduled transfers for the player."""

    def __init__(self, game_model: GameModel) -> None:
        super().__init__()

        self.game_model = game_model
        self.coalition = self.game_model.game.coalition_for(
            self.game_model.game.is_player_blue
        )
        self.air_wing = self.coalition.air_wing
        try:
            self.reserve_squadrons = self.coalition.reserve_quotas
        except AttributeError:
            self.reserve_squadrons = {}
        self.reserve_groups = {}

        self.setWindowTitle(f"Buy Quotas")

        main_layout = QVBoxLayout()

        scroll_content = QWidget()
        task_box_layout = QGridLayout()
        row = 0

        unit_types: Set[AircraftType] = set()

        for squadron in self.air_wing.iter_squadrons():
            unit_types.add(squadron.aircraft)

        sorted_squadrons = sorted(
            self.air_wing.iter_squadrons(),
            key=lambda s: (s.location.name, s.aircraft.display_name),
        )
        for row, squadron in enumerate(sorted_squadrons):
            self.add_purchase_row(squadron, task_box_layout, row)

        stretch = QVBoxLayout()
        stretch.addStretch()
        task_box_layout.addLayout(stretch, row, 0)

        scroll_content.setLayout(task_box_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def current_quantity_of(self, squadron: Squadron) -> int:
        return self.reserve_squadrons.get(squadron, 0)

    @staticmethod
    def minimum_quota(squadron: Squadron) -> int:
        return 0

    @staticmethod
    def maximum_quota(squadron: Squadron) -> int:
        return squadron.max_size

    @staticmethod
    def display_name_of(squadron: Squadron) -> str:
        return "<br />".join([squadron.aircraft.display_name, squadron.location.name])

    @staticmethod
    def aircraft_info_of(squadron: Squadron) -> str:
        return "<br />".join([str(squadron), f"$ {squadron.aircraft.price} M"])

    @staticmethod
    def home_base_of(squadron: Squadron) -> str:
        return squadron.location.name

    @staticmethod
    def price_of(squadron: Squadron) -> int:
        return squadron.aircraft.price

    def lower_quota(self, squadron: Squadron) -> None:
        quantity = self.current_quantity_of(squadron)
        self.reserve_squadrons[squadron] = quantity - 1 if quantity > 0 else quantity
        self.post_transaction_update()

    def increase_quota(self, squadron: Squadron) -> None:
        quantity = self.current_quantity_of(squadron)
        self.reserve_squadrons[squadron] = (
            quantity + 1 if quantity < squadron.max_size else quantity
        )
        self.post_transaction_update()

    def info(self, squadron: Squadron) -> None:
        self.info_window = QUnitInfoWindow(self.game_model.game, squadron.aircraft)
        self.info_window.show()

    def add_purchase_row(
        self,
        item: Squadron,
        layout: QGridLayout,
        row: int,
    ) -> None:
        exist = QGroupBox()
        exist.setProperty("style", "buy-box")
        exist.setMaximumHeight(72)
        exist.setMinimumHeight(36)
        existLayout = QHBoxLayout()
        existLayout.setSizeConstraint(QLayout.SetMinimumSize)
        exist.setLayout(existLayout)

        unitName = QLabel(f"<b>{self.display_name_of(item)}</b>")
        unitName.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        )

        existing_units = self.current_quantity_of(item)
        existing_units = QLabel(str(existing_units))
        existing_units.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        aircraft_info = QLabel(self.aircraft_info_of(item))
        aircraft_info.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        aircraft_info.setAlignment(Qt.AlignRight)

        reserve_group = ReserveGroup(item, self)
        self.reserve_groups[item] = reserve_group

        current_units = item.owned_aircraft
        current_units = QLabel(str(current_units))
        current_units.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        current = QGroupBox()
        current.setProperty("style", "buy-box")
        current.setMaximumHeight(72)
        current.setMinimumHeight(36)
        currentlayout = QHBoxLayout()
        current.setLayout(currentlayout)

        info = QGroupBox()
        info.setProperty("style", "buy-box")
        info.setMaximumHeight(72)
        info.setMinimumHeight(36)
        infolayout = QHBoxLayout()
        info.setLayout(infolayout)

        unitInfo = QPushButton("i")
        unitInfo.setProperty("style", "btn-info")
        unitInfo.setMinimumSize(16, 16)
        unitInfo.setMaximumSize(16, 16)
        unitInfo.clicked.connect(lambda: self.info(item))
        unitInfo.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        existLayout.addWidget(unitName)
        existLayout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Minimum)
        )
        existLayout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Minimum)
        )
        existLayout.addWidget(aircraft_info)
        currentlayout.addWidget(current_units)
        infolayout.addWidget(unitInfo)

        layout.addWidget(exist, row, 1)
        layout.addWidget(current, row, 2)
        layout.addWidget(reserve_group, row, 3)
        layout.addWidget(info, row, 4)

    def update_purchase_controls(self) -> None:
        coalition = self.game_model.game.coalition_for(
            self.game_model.game.is_player_blue
        )
        for group in self.reserve_groups.values():
            group.update_state()
        coalition.reserve_quotas = self.reserve_squadrons

        coalition.budget = ProcurementAi(
            coalition.game,
            self.game_model.game.is_player_blue,
            coalition.faction,
            False,
            False,
            False,
            coalition.reserve_quotas or {},
        ).spend_budget(coalition.budget)

    def update_available_budget(self) -> None:
        GameUpdateSignal.get_instance().updateBudget(self.game_model.game)

    def post_transaction_update(self) -> None:
        self.update_purchase_controls()
        self.update_available_budget()


class ReserveGroup(QGroupBox):
    def __init__(self, item: Squadron, buy_quota: BuyQuotasDialog) -> None:
        super().__init__()
        self.item = item
        self.buy_quota = buy_quota
        self.setProperty("style", "buy-box")
        self.setMaximumHeight(72)
        self.setMinimumHeight(36)
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.sell_button = QPushButton("-")
        self.sell_button.setProperty("style", "btn-sell")
        self.sell_button.setDisabled(not self.enable_sale(self.item))
        self.sell_button.setMinimumSize(16, 16)
        self.sell_button.setMaximumSize(16, 16)
        self.sell_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        )

        self.sell_button.clicked.connect(lambda: self.buy_quota.lower_quota(self.item))

        self.amount_bought = QLabel()
        self.amount_bought.setSizePolicy(
            QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        )

        self.buy_button = QPushButton("+")
        self.buy_button.setProperty("style", "btn-buy")
        self.buy_button.setDisabled(not self.enable_purchase(self.item))
        self.buy_button.setMinimumSize(16, 16)
        self.buy_button.setMaximumSize(16, 16)

        self.buy_button.clicked.connect(
            lambda: self.buy_quota.increase_quota(self.item)
        )
        self.buy_button.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        layout.addWidget(self.sell_button)
        layout.addWidget(self.amount_bought)
        layout.addWidget(self.buy_button)

        self.update_state()

    def enable_sale(self, squadron: Squadron):
        return self.buy_quota.current_quantity_of(
            squadron
        ) > self.buy_quota.minimum_quota(squadron)

    def enable_purchase(self, squadron: Squadron):
        return self.buy_quota.current_quantity_of(
            squadron
        ) < self.buy_quota.maximum_quota(squadron)

    def update_state(self) -> None:
        self.buy_button.setEnabled(self.enable_purchase(self.item))
        self.sell_button.setEnabled(self.enable_sale(self.item))
        self.amount_bought.setText(
            f"<b>{self.buy_quota.current_quantity_of(self.item)}</b>"
        )
