import json
import time
import math

from file_databases import JsonDb, FileAppend


def last(in_list, default):
    try:
        return in_list[-1]
    except IndexError:
        return default


class Error:
    def __init__(self, code: int, text: str):
        self.code = code
        self.text = text

    def __bool__(self):
        if self.code in [200, 201, 202]:
            return False
        return True


OK = Error(200, "OK")
CORRUPTED_ELO_DB = Error(500, "Fatal: Possibly Corrupted elo db")

NEW_PLAYER_DATA = {"elo": 1000, "num_games": 0, "last_played": int(time.time()), "multiplier": 160}
PHANTOM_PLAYER_DATA = json.dumps({"elo": 1000, "num_games": 0, "last_played": 0, "multiplier": 160})


class EloRepo:
    def __init__(self, db="../data/elo.json", matches_db="../data/matches.txt"):
        self.db = JsonDb(db, keys=["elo", "num_games", "last_played", "multiplier"])
        self.matches_db = FileAppend(matches_db)

    def getall(self):
        content = self.db.get()
        try:
           out = [{"name": name, "elo": val["elo"]} for name, val in content.items()]
        except KeyError:
            return None, CORRUPTED_ELO_DB
        return out, OK

    def get_games_for_player(self, name):
        victories = self.matches_db.query(0, name)
        losses = self.matches_db.query(1, name)
        victories = [{"winner": x[0], "loser":x[1], "time": int(x[2])} for x in victories]
        losses = [{"winner": x[0], "loser":x[1], "time": int(x[2])} for x in losses]
        return {"victories": victories, "losses": losses}, OK

    def get_last_n_games(self, n):
        games = self.matches_db.query(0, None)

        games = [{"winner": x[0], "loser": x[1], "time": int(x[2])} for x in games]
        try:
            games = games[-n:]
        except IndexError:
            pass
        return games, OK

    def getone(self, name):
        row, ok = self.db.get_one(name)
        if not ok:
            return {"elo":1000}, OK
        try:
            return {"elo": row["elo"]}, OK
        except KeyError:
            return None, CORRUPTED_ELO_DB

    def register_match(self, winner, loser):
        winner_row, ok = self.db.get_one(winner)
        if not ok:
            winner_row = NEW_PLAYER_DATA.copy()

        loser_row, ok = self.db.get_one(loser)
        if not ok:
            loser_row = NEW_PLAYER_DATA.copy()
        expected_prob = 1 / (1 + math.pow(10, (loser_row["elo"] - winner_row["elo"])/400))
        change = (1 - expected_prob)
        winner_row["elo"] += int(change * winner_row["multiplier"])
        loser_row["elo"] -= int(change * loser_row["multiplier"])
        winner_row["num_games"] += 1
        loser_row["num_games"] += 1
        self.update_multiplier(winner_row)
        self.update_multiplier(loser_row)
        winner_row["last_played"] = int(time.time())
        loser_row["last_played"] = int(time.time())
        self.db.updaterow(winner, winner_row)
        self.db.updaterow(loser, loser_row)
        self.matches_db.write(winner, loser, str(int(time.time())), json.dumps(winner_row), json.dumps(loser_row))
        return OK

    def undo_match(self, winner, loser):

        winner_row, ok = self.db.get_one(winner)
        if not ok:
            return CORRUPTED_ELO_DB
        loser_row, ok = self.db.get_one(loser)
        if not ok:
            return CORRUPTED_ELO_DB
        last_winner_w = last(self.matches_db.query(0, winner), [0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        last_winner_l = last(self.matches_db.query(1, winner), [0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        last_loser_w = last(self.matches_db.query(0, loser), [0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        last_loser_l = last(self.matches_db.query(1, loser), [0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        if int(last_winner_w[2]) > int(last_winner_l[2]):
            new_winner_row = json.loads(last_winner_w[3])
        else:
            new_winner_row = json.loads(last_winner_l[4])
        if int(last_loser_w[2]) > int(last_loser_l[2]):
            new_loser_row = json.loads(last_loser_w[3])
        else:
            new_loser_row = json.loads(last_loser_l[4])

        self.db.updaterow(winner, new_winner_row)
        self.db.updaterow(loser, new_loser_row)
        if new_winner_row["num_games"] == 0:
            self.db.delete_one(winner)
        if new_loser_row["num_games"] == 0:
            self.db.delete_one(loser)
        return OK

    @staticmethod
    def update_multiplier(row):
        base = 40
        if row["elo"] > 2400:
            row["multiplier"] = 10
            return
        if row["num_games"] < 15:
            base = 20
        temp_multiplier = row["multiplier"]/base
        if row["num_games"] == 15:
            temp_multiplier = temp_multiplier / 2
        years_passed = (time.time() - row["last_played"]) / (86400 * 365)
        temp_multiplier = min(temp_multiplier * (1 + years_passed*2), 8)
        temp_multiplier = math.pow(temp_multiplier, 0.9)
        out = min(base * temp_multiplier, 160)
        row["multiplier"] = out
        return

    def undo(self):
        last_row = self.matches_db.pop_last()
        res = self.undo_match(last_row[0], last_row[1])
        return res


