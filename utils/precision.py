from decimal import Decimal, ROUND_DOWN


def _get_increment(info: dict) -> Decimal:
    """
    Pick the tightest increment Coinbase returns for this product.
    In V3 the name is usually `trading_increment`; in V2 it’s `base_increment`.
    """
    for key in ("trading_increment", "base_increment", "quote_increment"):
        inc = info.get(key)
        if inc and Decimal(inc) > 0:
            return Decimal(inc)
    # Fallback – should never happen:
    return Decimal("0.00000001")


def format_size(cb_client, product_id: str, raw_size: float) -> str:
    """
    Truncate raw_size to the product's allowed increment.

    ▸ cb_client   –  coinbase.rest.RESTClient instance
    ▸ product_id  –  e.g. "LINK-USD"
    ▸ raw_size    –  float you intend to trade

    Returns a string without superfluous trailing zeros.
    """
    info = cb_client.get_product(product_id).to_dict()
    inc  = _get_increment(info)                       # ← NEW logic
    size = (Decimal(str(raw_size))                    # preserve precision
            .quantize(inc, rounding=ROUND_DOWN))      # truncate
    return format(size.normalize(), "f")              # plain decimal text