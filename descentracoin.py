from coin import Coin

class DescentraCoin(Coin):
    def __init__(self, amount):
        super().__init__("DSC", "Descentra Coin", amount)

    @classmethod
    def from_dict(cls, coin_dict):
        """
        Crea una instancia de DescentraCoin a partir de un diccionario.
        """
        return cls(
            amount=coin_dict.get("value", 0)  # Usando get para manejar valores por defecto
        )
    