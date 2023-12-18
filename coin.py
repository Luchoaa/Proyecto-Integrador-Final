class Coin:
    def __init__(self, symbol, name, value=0):
        self.symbol = symbol
        self.name = name
        self.value = value

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "name": self.name,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, coin_dict):
        """
        Crea una instancia de Coin a partir de un diccionario.
        """
        return cls(
            symbol=coin_dict["symbol"],
            name=coin_dict["name"],
            value=coin_dict.get("value", 0)  # Usando get para manejar valores por defecto
        )

    def __add__(self, other):
        if isinstance(other, Coin):
            if self.symbol != other.symbol:
                raise ValueError("Different coin types cannot be added.")
            return Coin(self.symbol, self.name, self.value + other.value)
        elif isinstance(other, (int, float)):  # Handling numeric values
            return Coin(self.symbol, self.name, self.value + other)
        else:
            raise ValueError("Unsupported type for addition.")

    def __sub__(self, other):
        if isinstance(other, Coin):
            if self.symbol != other.symbol:
                raise ValueError("Different coin types cannot be subtracted.")
            if self.value < other.value:
                raise ValueError("Insufficient coin value.")
            return Coin(self.symbol, self.name, self.value - other.value)
        elif isinstance(other, (int, float)):  # Handling numeric values
            return Coin(self.symbol, self.name, self.value - other)
        else:
            raise ValueError("Unsupported type for subtraction.")

    def __str__(self):
        return f"{self.value} {self.symbol}"
    
    def __lt__(self, other):
        if isinstance(other, Coin):
            return self.value < other.value
        raise TypeError("Unsupported type for comparison.")

    def __le__(self, other):
        if isinstance(other, Coin):
            return self.value <= other.value
        raise TypeError("Unsupported type for comparison.")

    def __gt__(self, other):
        if isinstance(other, Coin):
            return self.value > other.value
        raise TypeError("Unsupported type for comparison.")

    def __ge__(self, other):
        if isinstance(other, Coin):
            return self.value >= other.value
        raise TypeError("Unsupported type for comparison.")

    def __eq__(self, other):
        if isinstance(other, Coin):
            return self.value == other.value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)
    
if __name__ == "__main__":
    # Prueba de la clase Coin y sus métodos to_dict y from_dict

    # Crear una instancia de Coin
    original_coin = Coin(symbol="DSC", name="DescentraCoin", value=100)

    # Convertir la moneda a un diccionario
    coin_dict = original_coin.to_dict()
    print("Coin como diccionario:", coin_dict)

    # Crear una nueva instancia de Coin a partir del diccionario
    new_coin = Coin.from_dict(coin_dict)
    print("Nueva instancia de Coin:", new_coin)

    # Comprobar si la nueva instancia es igual a la original
    assert original_coin == new_coin, "Las instancias de Coin no son iguales"

    # Si no hay errores, la prueba es exitosa
    print("Prueba exitosa: La nueva instancia es igual a la original")