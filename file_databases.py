import json
import time


class Reserver:
    def __init__(self, reserver):
        self.reserver = reserver

    def reserve(self):
        counter = 0
        exit = False

        while counter < 100 and not exit:
            with open(self.reserver, "r") as f:
                if f.read() == "BUSY":
                    counter = counter + 1
                    time.sleep(0.01)
                    continue
                exit = True

        with open(self.reserver, "w+") as f:
            f.write("BUSY")

    def free(self):
        with open(self.reserver, "w+") as f:
            f.write("FREE")


class JsonDb(Reserver):
    def __init__(self, path, keys):
        self.path = path

        reserver = ".".join(self.path.split(".")[:-1]) + "_reserver.txt"
        Reserver.__init__(self, reserver)
        self.value = dict()
        self.keys = set(keys)
        self.load()
        self.free()

    def load(self):
        with open(self.path, "r+") as f:
            self.value = json.load(f)

    def sort(self):
        sorted_items = sorted(list(self.value.items()), key=lambda x: x[1]["elo"], reverse=True)
        print(sorted_items)
        print("sorted_items_above")
        self.value = {k: v for k, v in sorted_items}

    def save(self):
        self.reserve()
        print(f"saving value {self.value}")
        print(f"items: {self.value.items()}")

        print(f"saving value {self.value}")
        self.sort()
        print(f"sorted value {self.value}")
        with open(self.path, "w") as f:
            json.dump(self.value, f)
        self.free()

    def updaterow(self, name, newrow):
        self.load()
        if name not in self.value.keys():
            if set(newrow.keys()) != self.keys:
                print(set(newrow.keys()))
                print(self.keys)
                raise ValueError
            self.value[name] = newrow
            print(f"should be 'dict'': {type(self.value[name])}")
            self.save()
            return
        if not set(newrow.keys()).issubset(self.keys):
            raise ValueError
        self.value[name].update(newrow)
        self.save()

    def get(self):
        self.load()
        return self.value

    def get_one(self, name):
        self.load()
        out = self.value.get(name)
        if out is None:
            return out, False
        return out, True

    def delete_one(self, name):
        self.load()
        try:
            del self.value[name]
        except KeyError:
            pass
        self.save()


class FileAppend(Reserver):
    def __init__(self, path, num_parts=5):
        self.path = path
        self.num_parts = num_parts
        reserver = ".".join(self.path.split(".")[:-1]) + "_reserver.txt"
        Reserver.__init__(self, reserver)
        with open(self.reserver, "w+") as f:
            f.write("FREE")

    def write(self, *args):
        if len(args) != self.num_parts:
            raise ValueError
        self.reserve()
        with open(self.path, "a+") as f:
            f.write(",,,".join(list(args)) + "\n")
        self.free()

    def pop_last(self):
        self.reserve()
        with open(self.path, "r") as f:
            out = f.readlines()
            if len(out) == 0:
                self.free()
                return
            retval = out[-1]
            out = out[:-1]

        with open(self.path, "w+") as f:
            f.writelines(out)
        self.free()
        return retval.split(",,,")

    def query(self, position, value):
        with open(self.path, "r") as f:
            content = f.readlines()
        return [x.split(",,,") for x in content if x.split(",,,")[position] == value]