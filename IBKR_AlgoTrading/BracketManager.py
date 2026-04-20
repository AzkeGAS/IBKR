from ibapi.order import Order


class BracketManager:
    def __init__(self, app, contract, quantity, tick_round=2):
        self.app = app
        self.contract = contract
        self.qty = quantity
        self.tick_round = tick_round

        # One bracket per side
        self.brackets = {
            "BUY": None,
            "SELL": None
        }

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def can_place(self, side):
        """Allow only one bracket per side"""
        return self.brackets[side] is None

    def place_bracket(self, side, entry, tp, sl, order_id):
        """
        Places a full IB bracket order
        """
        if not self.can_place(side):
            print(f"{side} bracket already active")
            return

        parent = self._parent_order(order_id, side, entry)
        tp_order = self._tp_order(order_id + 1, side, tp, order_id)
        sl_order = self._sl_order(order_id + 2, side, sl, order_id)

        self.app.placeOrder(parent.orderId, self.contract, parent)
        self.app.placeOrder(tp_order.orderId, self.contract, tp_order)
        self.app.placeOrder(sl_order.orderId, self.contract, sl_order)

        self.brackets[side] = {
            "parent": order_id,
            "tp_id": order_id + 1,
            "sl_id": order_id + 2,
            "last_tp_price": tp,
            "current_sl_price": sl,
            "parent_filled": False
        }

        print(f"{side} bracket placed")

    def on_order_status(self, orderId, status, parentId):
        """
        Call this from EWrapper.orderStatus
        """
        for side, b in self.brackets.items():
            if not b:
                continue

            # Parent filled
            if orderId == b["parent"] and status == "Filled":
                b["parent_filled"] = True

            # Any final state cancels whole bracket
            if status in ("Cancelled", "Inactive"):
                if orderId in (b["parent"], b["tp_id"], b["sl_id"]):
                    self._clear(side)

    def maybe_update_stop_after_tp_move(self, side, new_tp_price, stop_offset):
        """
        Move STOP only if TP improves
        """
        b = self.brackets.get(side)
        if not b or not b["parent_filled"]:
            return

        last_tp = b["last_tp_price"]
        current_sl = b["current_sl_price"]

        if side == "BUY":
            # TP must increase
            if new_tp_price <= last_tp:
                return

            proposed_sl = round(new_tp_price - stop_offset, self.tick_round)
            if proposed_sl <= current_sl:
                return

            action = "SELL"

        else:  # SELL
            if new_tp_price >= last_tp:
                return

            proposed_sl = round(new_tp_price + stop_offset, self.tick_round)
            if proposed_sl >= current_sl:
                return

            action = "BUY"

        stop = Order()
        stop.orderId = b["sl_id"]
        stop.action = action
        stop.orderType = "STP"
        stop.totalQuantity = self.qty
        stop.auxPrice = proposed_sl
        stop.transmit = True

        self.app.placeOrder(stop.orderId, self.contract, stop)

        b["last_tp_price"] = new_tp_price
        b["current_sl_price"] = proposed_sl

        print(f"{side} STOP updated → {proposed_sl}")

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _clear(self, side):
        print(f"{side} bracket cleared")
        self.brackets[side] = None

