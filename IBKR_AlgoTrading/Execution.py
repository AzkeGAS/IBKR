def execDetails(self, reqId, contract, execution):
    print(f"✅ EXECUTION: {execution.execId}")
    print(f"   OrderId: {execution.orderId}")
    print(f"   Side: {execution.side}")
    print(f"   Shares: {execution.shares}")
    print(f"   Price: {execution.price}")
    print(f"   Time: {execution.time}")

    # Track position properly
    if execution.side == "BOT":
        self.in_position_long = True
        self.entry_price = execution.price

    elif execution.side == "SLD":
        self.in_position_short = True
        self.entry_price = execution.price

    order_id = execution.orderId
    side = execution.side
    qty = execution.shares
    price = execution.price

    print(f"EXEC: {order_id} | {side} | {qty} @ {price}")

    # -------- LONG ENTRY --------
    if self.longbracket["active"] and order_id == self.longbracket["parent_id"]:
        self.in_position_long = True
        self.entry_price = price
        print("🟢 LONG ENTRY FILLED")

    # -------- SHORT ENTRY --------
    elif self.shortbracket["active"] and order_id == self.shortbracket["parent_id"]:
        self.in_position_short = True
        self.entry_price = price
        print("🔴 SHORT ENTRY FILLED")

    # -------- LONG EXIT --------
    elif self.longbracket["active"] and order_id == self.longbracket["sl_id"]:
        self.in_position_long = False
        self.longbracket["active"] = False
        print("❌ LONG STOP HIT")

    # -------- SHORT EXIT --------
    elif self.shortbracket["active"] and order_id == self.shortbracket["sl_id"]:
        self.in_position_short = False
        self.shortbracket["active"] = False
        print("❌ SHORT STOP HIT")