
active_brackets = {
    "BUY": None,   # parentOrderId or None
    "SELL": None
}

#Use orderStatus callback
def orderStatus(
    self, orderId, status, filled, remaining,
    avgFillPrice, permId, parentId, lastFillPrice,
    clientId, whyHeld, mktCapPrice
):

    print(f"Order {orderId} status: {status}")

    # Parent order finished or cancelled → free the slot
    if status in ("Cancelled", "Inactive"):
        self.clear_if_parent(orderId)

    # Parent filled → still active until children finish
      
#When placing a bracket, record the parent orderId AND side:


def register_parent(self, orderId, action):
    self.active_brackets[action] = orderI

# Prevent More Than One Bracket Per Side
def can_place_bracket(self, action):
    return self.active_brackets[action] is Non

#Usage
if app.can_place_bracket("BUY"):
    app.place_buy_bracket()
else:
    print("BUY bracket already active"

          
def clear_if_parent(self, orderId):
    for side, parent_id in self.active_brackets.items():
        if parent_id == orderId:
            self.active_brackets[side] = None
            print(f"{side} bracket released")

# Clearing the Bracket Slot
if signal == "LONG" and app.can_place_bracket("BUY"):
    place_buy_bracket()

if signal == "SHORT" and app.can_place_bracket("SELL"):
    place_sell_bracket()


