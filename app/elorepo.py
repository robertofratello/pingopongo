import json
import time
import math
import os
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


WINNER = 0
LOSER = 1
TIME = 2
WINNER_DATA = 3
LOSER_DATA = 4

OK = Error(200, "OK")
CORRUPTED_ELO_DB = Error(500, "Fatal: Possibly Corrupted elo db")
CORRUPTED_MATCHES_DB = Error(500, "Fatal: Possibly Corrupted matches db")
NOTHING_TO_REDO = Error(204, "No match to redo found in database")
NEW_PLAYER_DATA = {"elo": 1000, "num_games": 0, "isActive": True,
                   "last_played": int(time.time()), "multiplier": 160}
PHANTOM_PLAYER_DATA = json.dumps(
    {"elo": 1000, "isActive": False, "num_games": 0, "last_played": 0, "multiplier": 160})


class EloRepo:
    def __init__(self, db="../data/default/elo.json", matches_db="../data/default/matches.txt", undo_db="../data/default/undone_matches.txt"):
        os.makedirs(os.path.dirname(db), exist_ok=True)
        self.db = JsonDb(
            db, keys=["elo", "isActive", "num_games", "last_played", "multiplier"])
        self.matches_db = FileAppend(matches_db)
        self.undo_db = FileAppend(undo_db)

    def get_dbs(self, db):
        if not db:
            return self.db, self.matches_db
        os.makedirs(db, exists_ok=True)
        if not os.path.exists(db):
            print("makedirs is not working")
            raise ValueError
        print(f"directory exists with path {db}")

        return JsonDb("../data/" + db + "/elo.json",
                      keys=["elo", "isActive", "num_games", "last_played", "multiplier"]), FileAppend(db + "/matches.txt")

    def get_undo_db(self, db):
        if not db:
            return self.undo_db
        return FileAppend("../data/" + db + "undone_matches.txt")

    def getall(self, db):
        db, _ = self.get_dbs(db)
        content = db.get()
        print([(name, val) for name, val in content.items()])
        try:
            out = [{"name": name, "elo": val["elo"], "isActive": val["isActive"]}
                   for name, val in content.items()]
        except KeyError:
            return None, CORRUPTED_ELO_DB
        return out, OK

    def get_games_for_player(self, name, db):
        db, matches_db = self.get_dbs(db)
        victories = matches_db.query(0, name)
        losses = matches_db.query(1, name)
        victories = [{"winner": x[WINNER], "loser": x[LOSER],
                      "time": int(x[TIME]), "elo": json.loads(x[WINNER_DATA])["elo"]} for x in victories]
        losses = [{"winner": x[WINNER], "loser": x[LOSER],
                   "time": int(x[TIME]), "elo": json.loads(x[LOSER_DATA])["elo"]} for x in losses]
        all_matches = victories + losses
        all_matches.sort(key=lambda x: x["time"], reverse=True)
        return all_matches, OK

    def get_last_n_games(self, n, db):

        db, matches_db = self.get_dbs(db)
        games = matches_db.query(0, None)

        games = [{"winner": x[WINNER], "loser": x[LOSER],
                  "time": int(x[TIME]), "winner_elo": json.loads(x[WINNER_DATA])["elo"], 
                  "loser_elo": json.loads(x[LOSER_DATA])["elo"]} for x in games]
        try:
            games = games[-n:]
        except IndexError:
            pass
        return games, OK

    def getone(self, name, db):

        db, matches_db = self.get_dbs(db)
        row, ok = db.get_one(name)
        if not ok:
            return {"elo": 1000}, OK
        try:
            return {"elo": row["elo"], "isActive": row["isActive"]}, OK
        except KeyError:
            return None, CORRUPTED_ELO_DB

    def compute_elo_change_from_rows(self, winner_row, loser_row):
        """ Returns the elo change of the winner and the loser, as a tuple. """
       
        expected_prob = 1 / \
            (1 + math.pow(10, (loser_row["elo"] - winner_row["elo"])/400))
        change = (1 - expected_prob)
        return int(change * winner_row["multiplier"]), -int(change * loser_row["multiplier"]), OK
    
    def compute_elo_change(self, winner, loser, db, timestamp=None):
        if timestamp is None:
            timestamp = str(int(time.time()))
        elo_db, _ = self.get_dbs(db)

        winner_row, ok = elo_db.get_one(winner)
        if not ok:
            winner_row = NEW_PLAYER_DATA.copy()

        loser_row, ok = elo_db.get_one(loser)
        if not ok:
            loser_row = NEW_PLAYER_DATA.copy()
        self.add_inactivity_boost(winner_row, timestamp)
        self.add_inactivity_boost(loser_row, timestamp)
        
        winner_change, loser_change, _ = self.compute_elo_change_from_rows(
            winner_row, loser_row)
        return winner_change, loser_change, OK

        

    def register_match(self, winner, loser, db, timestamp=None, clear_undo=True):
        if timestamp is None:
            timestamp = str(int(time.time()))
        undo_db = self.get_undo_db(db)
        elo_db, matches_db = self.get_dbs(db)

        winner_row, ok = elo_db.get_one(winner)
        if not ok:
            winner_row = NEW_PLAYER_DATA.copy()

        loser_row, ok = elo_db.get_one(loser)
        if not ok:
            loser_row = NEW_PLAYER_DATA.copy()
        self.add_inactivity_boost(winner_row, timestamp)
        self.add_inactivity_boost(loser_row, timestamp)
        
        winner_change, loser_change, _ = self.compute_elo_change_from_rows(
            winner_row, loser_row)
        winner_row["elo"] += winner_change
        loser_row["elo"] += loser_change
        winner_row["num_games"] += 1
        loser_row["num_games"] += 1
        self.update_multiplier(winner_row, timestamp)
        self.update_multiplier(loser_row, timestamp)
        winner_row["last_played"] = timestamp
        loser_row["last_played"] = timestamp
        elo_db.updaterow(winner, winner_row)
        elo_db.updaterow(loser, loser_row)
        matches_db.write(winner, loser, timestamp, json.dumps(
            winner_row), json.dumps(loser_row))
        if clear_undo:
            undo_db.clear()
        return OK

    def undo_match(self, winner, loser, db):

        db, matches_db = self.get_dbs(db)
        winner_row, ok = db.get_one(winner)
        if not ok:
            return CORRUPTED_ELO_DB
        loser_row, ok = db.get_one(loser)
        if not ok:
            return CORRUPTED_ELO_DB
        last_winner_w = last(matches_db.query(0, winner), [
                             0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        last_winner_l = last(matches_db.query(1, winner), [
                             0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        last_loser_w = last(matches_db.query(0, loser), [
                            0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        last_loser_l = last(matches_db.query(1, loser), [
                            0, 0, 0, PHANTOM_PLAYER_DATA, PHANTOM_PLAYER_DATA])
        if int(last_winner_w[TIME]) > int(last_winner_l[TIME]):
            new_winner_row = json.loads(last_winner_w[WINNER_DATA])
        else:
            new_winner_row = json.loads(last_winner_l[LOSER_DATA])
        if int(last_loser_w[TIME]) > int(last_loser_l[TIME]):
            new_loser_row = json.loads(last_loser_w[WINNER_DATA])
        else:
            new_loser_row = json.loads(last_loser_l[LOSER_DATA])

        db.updaterow(winner, new_winner_row)
        db.updaterow(loser, new_loser_row)
        if new_winner_row["num_games"] == 0:
            db.delete_one(winner)
        if new_loser_row["num_games"] == 0:
            db.delete_one(loser)
        return OK

    @staticmethod
    def update_multiplier(row, timestamp):
        base = 40
        if row["elo"] > 2400:
            row["multiplier"] = 10
            return
        if row["num_games"] < 15:
            base = 20
        if row["num_games"] == 15:
            row["multiplier"] = row["multiplier"]/2
        row["multiplier"] = row["multiplier"] * 0.9
        row["multiplier"] = max(base, row["multiplier"])
        row["multiplier"] = min(row["multiplier"], 160)
 
    
    @staticmethod 
    def add_inactivity_boost(row, timestamp): 
        years_passed = (int(timestamp) -
                        int(row["last_played"])) / (86400 * 365)
        if years_passed > 1/12:
            row["multiplier"] = row["multiplier"] * min((1 + years_passed * 3.5), 8)
        row["multiplier"] = min(row["multiplier"], 160)

        
    def undo(self, db):
        _, matches_db = self.get_dbs(db)
        last_row = matches_db.pop_last()
        if len(last_row) != 5:
            return CORRUPTED_MATCHES_DB
        self.undo_db.write(*last_row)
        res = self.undo_match(last_row[0], last_row[1], db)
        return res

    def redo(self, db):
        undo_db = self.get_undo_db(db)
        last_row = undo_db.pop_last()

        if last_row is None:
            return NOTHING_TO_REDO
        assert len(last_row) == 5, len(last_row)
        res = self.register_match(
            last_row[WINNER], last_row[LOSER], db, timestamp=last_row[TIME], clear_undo=False)
        _, matches_db = self.get_dbs(db)
        matches_db.sort_by(TIME)

        return res
