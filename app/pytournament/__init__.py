class Player: 
    def __init__(self, name, elo):
        self.name = name 
        self.elo = elo 

class Players: 
    def __init__(self, players):
        self.players = players 
    
    @classmethod 
    def from_dicts(self, players_list): 
        players = [Player(x["name"], x.get("elo", 1000)) for x in players_list]

class TournamentModel: 
    def __init__(self, submodels, num_players): 
        assert len(self.submodels) == num_players
    
      