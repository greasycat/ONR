import numpy as np
from analysis.grid import Grid
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches


# H11 W11
# TopLeft 0.5, 225
# TopRight 227 225
# BottomLeft 0.5 -1
# BottomRight 227 -1
# for key, value in subjects.movement_sequence.items():

class Shortcuts:
    def __init__(self, dict_generator):
        self.shortcuts = {}
        for row in dict_generator:
            source = row["Source"]
            destination = row["Destination"]
            distance = float(row["Distance"])
            inner_dict = {destination: distance}
            if source in self.shortcuts.keys():
                self.shortcuts[source].update(inner_dict)
            else:
                self.shortcuts[source] = inner_dict

    def get_shortcut(self, a, b):
        try:
            return self.shortcuts[a][b]
        except KeyError:
            pass
        try:
            return self.shortcuts[b][a]
        except KeyError:
            return None


class MovementData:
    def __init__(self, trial_name, trial_number, trial_time, x, y, rotation):
        self.y = y
        self.x = x
        self.trial_time = trial_time
        self.trial_name = trial_name
        self.trial_number = trial_number
        self.rotation = rotation

    def get_vector(self):
        """:return np.ndarray"""
        return np.array([float(self.x), float(self.y)])

    @staticmethod
    def from_str(s=""):
        """:return MovementData"""
        elements = [element.strip() for element in s.split(",")]
        if len(elements) < 6:
            return None
        return MovementData(elements[0], elements[1], elements[2], elements[3], elements[4], elements[5])


class MovementAnalyzer:
    def __init__(self, loader, origin=np.array([0.6, -1.1]), map_actual_size=np.array([226, 226]),
                 grid_size=np.array([11, 11])):
        self.grid = Grid(origin=origin, map_actual_size=map_actual_size, grid_size=grid_size)
        self.walls = loader.walls
        self.shortcut = loader.shortcuts
        self.trial_configuration = loader.trial_configuration
        self.current_subject = None
        self.bg_1 = loader.image_maze1
        self.subjects = loader.subjects
        pass

    def load_xy(self, subject, trial_number):
        """:return np.ndarray,np.ndarray"""
        try:
            self.current_subject = subject
            path = []
            last_moved_block = np.zeros(2)
            for move in subject.movement_sequence[trial_number]:
                current_pos = self.grid.get_block_pos(move.get_vector())
                if np.array_equal(last_moved_block, current_pos):
                    continue
                # Check offset
                offset = current_pos - last_moved_block
                if not np.array_equal(offset, current_pos) and offset.dot(offset) != 1:
                    correction_offset_1 = offset.copy()
                    correction_offset_2 = offset.copy()
                    correction_offset_1[0] = 0
                    correction_offset_2[1] = 0
                    correction_point_1 = correction_offset_1 + last_moved_block
                    correction_point_2 = correction_offset_2 + last_moved_block
                    if tuple(map(int, correction_point_1.tolist())) not in self.walls:
                        path.append(correction_point_1)
                    elif tuple(map(int, correction_point_2.tolist())) not in self.walls:
                        path.append(correction_point_2)
                    else:
                        pass

                path.append(current_pos)
                last_moved_block = current_pos

            arr = np.array(path)
            try:
                x = (arr[:, 0]) - 0.5
                y = (arr[:, 1]) - 0.5
            except IndexError:
                raise IndexError("No data for subject " + subject.name + " trial " + str(trial_number))

            return x, y

        except TypeError:
            raise KeyError("Make sure all the files are in the correct format, otherwise exclude the folder " + str(subject.name))
        except KeyError:
            raise KeyError("Make sure you've selected the proper range that matches the entries in the movement.csv " + str(subject.name))

    def draw(self, n, x, y, bg_file="", reverse_divide=False, capped=True):

        if bg_file == "":
            bg_file = self.bg_1

        fig, ax = plt.subplots()
        ax.step(x, y)

        plt.autoscale(False)
        bg = mpimg.imread(bg_file)
        plt.imshow(bg, extent=[0, self.grid.grid_size[0], 0, self.grid.grid_size[1]])

        if not self.shortcut:
            raise ValueError("Shortcuts not loaded")
            pass

        trial_name = self.current_subject.movement_sequence[n][0].trial_name
        source, destination = self.trial_configuration.get_source_destination_pair_by_name(trial_name)
        shortest = self.shortcut.get_shortcut(source, destination)
        estimated_distance = len(x)

        if reverse_divide:
            efficiency = shortest / estimated_distance
            if efficiency > 1 and capped:
                efficiency = 1
        else:
            efficiency = estimated_distance / shortest
            if efficiency < 1 and capped:
                efficiency = 1

        plt.title(
            f"Trial {n}@{trial_name}\n "
            f"From {source} to {destination}\n "
            f"Distance: {estimated_distance} "
            f"Shortest: {shortest} "
            f"Efficiency: {efficiency:.2f}")
        plt.xticks(np.arange(0, self.grid.grid_size[0] + 1, step=1))
        plt.yticks(np.arange(0, self.grid.grid_size[1] + 1, step=1))
        plt.grid()
        plt.show()

    def plot(self, subject, trial_number):
        x, y = self.load_xy(subject, trial_number)
        self.draw(trial_number, x, y)

    def plot_all(self, subject, start, end):
        for i in range(start, end+1):
            self.plot(subject, i)

    def calculate_efficiency(self, n, x, y, reverse_divide=False, capped=True):
        trial_name = self.current_subject.movement_sequence[n][0].trial_name
        source, destination = self.trial_configuration.get_source_destination_pair_by_name(trial_name)
        shortest = self.shortcut.get_shortcut(source, destination)
        estimated_distance = len(x)
        if reverse_divide:
            efficiency = shortest / estimated_distance
            if efficiency > 1 and capped:
                efficiency = 1
        else:
            efficiency = estimated_distance / shortest
            if efficiency < 1 and capped:
                efficiency = 1
        return efficiency

    def calculate_efficiency_for_one(self, subject, start, end, reverse_divide=False, capped=True):
        efficiency_dict = {}
        for n in range(start, end+1):
            x, y = self.load_xy(self.subjects[subject], n)
            efficiency_dict[n] = self.calculate_efficiency(n, x, y, reverse_divide, capped)
        return efficiency_dict

    def calculate_efficiency_for_all(self, start=3, end=23, excluding=None, reverse_divide=False, capped=True):
        if excluding is None:
            excluding = []

        efficiency_dict = {}
        for subject in self.subjects:
            if subject in excluding:
                continue
            efficiency_dict[subject] = self.calculate_efficiency_for_one(subject, start, end, reverse_divide, capped)
        return efficiency_dict
