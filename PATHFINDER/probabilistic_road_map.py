
import random
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import time
from scipy.spatial import distance

# parameter
N_SAMPLE = 500  # number of sample_points
N_KNN = 10  # number of edge from one sampled point
MAX_EDGE_LEN = 30.0  # [m] Maximum edge length

show_animation = False


class Node:
    """
    Node class for dijkstra search
    """

    def __init__(self, x, y, cost, parent_index):
        self.x = x
        self.y = y
        self.cost = cost
        self.parent_index = parent_index

    def __str__(self):
        return str(self.x) + "," + str(self.y) + "," +\
               str(self.cost) + "," + str(self.parent_index)


def prm_planning(sx, sy, gx, gy, ox, oy, rr):

    start_time = time.time()

    obstacle_kd_tree = cKDTree(np.vstack((ox, oy)).T)

    sample_x, sample_y = sample_points(sx, sy, gx, gy,
                                       rr, ox, oy, obstacle_kd_tree)
    if show_animation:
        plt.plot(sample_x, sample_y, ".b")

    road_map = generate_road_map(sample_x, sample_y, rr, obstacle_kd_tree)

    rx, ry = dijkstra_planning(
        sx, sy, gx, gy, road_map, sample_x, sample_y)

    dist = len(rx)
    end_time = time.time()
    elapsed_time = end_time - start_time

    return rx, ry, dist, elapsed_time


def is_collision(sx, sy, gx, gy, rr, obstacle_kd_tree):
    x = sx
    y = sy
    dx = gx - sx
    dy = gy - sy
    yaw = math.atan2(gy - sy, gx - sx)
    d = math.hypot(dx, dy)

    if d >= MAX_EDGE_LEN:
        return True

    D = rr
    n_step = round(d / D)

    for i in range(n_step):
        dist, _ = obstacle_kd_tree.query([x, y])
        if dist <= rr:
            return True  # collision
        x += D * math.cos(yaw)
        y += D * math.sin(yaw)

    # goal point check
    dist, _ = obstacle_kd_tree.query([gx, gy])
    if dist <= rr:
        return True  # collision

    return False  # OK


def generate_road_map(sample_x, sample_y, rr, obstacle_kd_tree):
    """
    Road map generation

    sample_x: [m] x positions of sampled points
    sample_y: [m] y positions of sampled points
    rr: Robot Radius[m]
    obstacle_kd_tree: KDTree object of obstacles
    """

    road_map = []
    n_sample = len(sample_x)
    sample_kd_tree = cKDTree(np.vstack((sample_x, sample_y)).T)

    for (i, ix, iy) in zip(range(n_sample), sample_x, sample_y):

        dists, indexes = sample_kd_tree.query([ix, iy], k=n_sample)
        edge_id = []

        for ii in range(1, len(indexes)):
            nx = sample_x[indexes[ii]]
            ny = sample_y[indexes[ii]]

            if not is_collision(ix, iy, nx, ny, rr, obstacle_kd_tree):
                edge_id.append(indexes[ii])

            if len(edge_id) >= N_KNN:
                break

        road_map.append(edge_id)

    #  plot_road_map(road_map, sample_x, sample_y)

    return road_map


def dijkstra_planning(sx, sy, gx, gy, road_map, sample_x, sample_y):
    """
    s_x: start x position [m]
    s_y: start y position [m]
    gx: goal x position [m]
    gy: goal y position [m]
    ox: x position list of Obstacles [m]
    oy: y position list of Obstacles [m]
    rr: robot radius [m]
    road_map: ??? [m]
    sample_x: ??? [m]
    sample_y: ??? [m]

    @return: Two lists of path coordinates ([x1, x2, ...], [y1, y2, ...]), empty list when no path was found
    """

    start_node = Node(sx, sy, 0.0, -1)
    goal_node = Node(gx, gy, 0.0, -1)

    open_set, closed_set = dict(), dict()
    open_set[len(road_map) - 2] = start_node

    path_found = True

    while True:
        if not open_set:
            print("Cannot find path")
            path_found = False
            break

        c_id = min(open_set, key=lambda o: open_set[o].cost)
        current = open_set[c_id]

        # show graph
        if show_animation and len(closed_set.keys()) % 2 == 0:
            # for stopping simulation with the esc key.
            plt.gcf().canvas.mpl_connect(
                'key_release_event',
                lambda event: [exit(0) if event.key == 'escape' else None])
            plt.plot(current.x, current.y, "xg")
            plt.pause(0.001)

        if c_id == (len(road_map) - 1):
            print("goal is found!")
            goal_node.parent_index = current.parent_index
            goal_node.cost = current.cost
            break

        # Remove the item from the open set
        del open_set[c_id]
        # Add it to the closed set
        closed_set[c_id] = current

        # expand search grid based on motion model
        for i in range(len(road_map[c_id])):
            n_id = road_map[c_id][i]
            dx = sample_x[n_id] - current.x
            dy = sample_y[n_id] - current.y
            d = math.hypot(dx, dy)
            node = Node(sample_x[n_id], sample_y[n_id],
                        current.cost + d, c_id)

            if n_id in closed_set:
                continue
            # Otherwise if it is already in the open set
            if n_id in open_set:
                if open_set[n_id].cost > node.cost:
                    open_set[n_id].cost = node.cost
                    open_set[n_id].parent_index = c_id
            else:
                open_set[n_id] = node

    if path_found is False:
        return [], []

    # generate final course
    rx, ry = [goal_node.x], [goal_node.y]
    parent_index = goal_node.parent_index
    while parent_index != -1:
        n = closed_set[parent_index]
        rx.append(n.x)
        ry.append(n.y)
        parent_index = n.parent_index

    return rx, ry


def plot_road_map(road_map, sample_x, sample_y):  # pragma: no cover

    for i, _ in enumerate(road_map):
        for ii in range(len(road_map[i])):
            ind = road_map[i][ii]

            plt.plot([sample_x[i], sample_x[ind]],
                     [sample_y[i], sample_y[ind]], "-k")


def sample_points(sx, sy, gx, gy, rr, ox, oy, obstacle_kd_tree):
    max_x = max(ox)
    max_y = max(oy)
    min_x = min(ox)
    min_y = min(oy)

    sample_x, sample_y = [], []

    while len(sample_x) <= N_SAMPLE:
        tx = (random.random() * (max_x - min_x)) + min_x
        ty = (random.random() * (max_y - min_y)) + min_y

        dist, index = obstacle_kd_tree.query([tx, ty])

        if dist >= rr:
            sample_x.append(tx)
            sample_y.append(ty)

    sample_x.append(sx)
    sample_y.append(sy)
    sample_x.append(gx)
    sample_y.append(gy)

    return sample_x, sample_y


def path(x, y):
    path = []
    for i in range(len(x)):
        path.append((x[i], y[i]))
    return path

def results(path):
    dist = 0
    for i in range(len(path)-1):
        dist = dist + distance.euclidean(path[i], path[i+1])
    
    return dist

def main():
    print(__file__ + " start!!")

    # start and goal position
    sx = 5.0
    sy = 5.0
    gx = 35.0
    gy = 71.0
    robot_size = 1.0

    ox = []
    oy = []
    obstacles_x = [14, 39, 67, 15, 2, 62, 27, 12, 47, 3, 98, 32, 46, 16, 82, 2, 20, 65, 43, 55, 95, 34, 76, 31, 28, 96, 29, 77, 57, 57, 73, 88, 14, 44, 71, 87, 47, 59, 77, 75, 41, 10, 10, 57, 48, 22, 93, 9, 94, 54, 88, 21, 23, 40, 94, 16, 57, 16, 62, 4, 87, 5, 96, 19, 40, 22, 9, 15, 80, 65, 94, 76, 18, 47, 70, 27, 36, 87, 81, 37, 80, 99, 9, 44, 44, 74, 91, 14, 54, 72, 95, 41, 30, 76, 75, 62, 17, 19, 57, 9, 33, 37, 29, 37, 97, 49, 83, 34, 32, 53, 21, 32, 67, 83, 55, 20, 62, 78, 98, 47, 92, 95, 78, 30, 48, 87, 44, 52, 5, 87, 9, 90, 83, 92, 20, 9, 11, 17, 38, 17, 73, 87, 4, 92, 9, 88, 81, 11, 64, 14, 90, 14, 27, 52, 96, 5, 32, 37, 71, 38, 67, 39, 44, 80, 96, 37, 43, 63, 92, 44, 77, 33, 80, 42, 85, 19, 10, 88, 70, 88, 9, 60, 86, 23, 20, 46, 94, 44, 61, 46, 90, 4, 16, 15, 73, 35, 83, 4, 96, 68, 46, 84, 84, 45, 58, 47, 19, 98, 47, 40, 74, 87, 73, 55, 42, 19, 90, 76, 31, 16, 34, 86, 72, 80, 82, 39, 84, 61, 22, 24, 85, 99, 30, 21, 97, 94, 16, 61, 37, 9, 80, 59, 28, 72, 93, 79, 12, 75, 78, 12, 58, 77, 31, 75, 55, 17, 77, 5, 95, 89, 29, 47, 15, 9, 46, 27, 55, 2, 62, 30, 84, 85, 52, 69, 38, 79, 77, 76, 58, 73, 58, 90, 43, 9, 38, 98, 90, 2, 98, 23, 24, 79, 26, 59, 91, 4, 76, 32, 75, 95, 22, 22, 19, 47, 61, 78, 17, 42, 37, 69, 94, 24, 86, 51, 4, 13, 96, 79, 63, 25, 72, 17, 32, 38, 36, 38, 52, 51, 58, 99, 2, 38, 84, 36, 10, 16, 32, 59, 44, 68, 98, 22, 49, 78, 89, 46, 80, 56, 74, 79, 72, 99, 62, 55, 46, 90, 73, 22, 39, 53, 72, 22, 79, 25, 11, 44, 97, 46, 14, 95, 28, 85, 13, 3, 30, 17, 51, 16, 12, 17, 7, 63, 35, 45, 89, 77, 92, 76, 56, 46, 4, 20, 73, 37, 34, 54, 56, 93, 45, 19, 83, 26, 61, 25, 79, 61, 10, 20, 52, 47, 65, 55, 40, 69, 31, 15, 48, 43, 43, 32, 27, 71, 88, 73, 37, 31, 75, 65, 24, 59, 82, 91, 46, 17, 43, 86, 54, 83, 40, 76, 2, 78, 65, 37, 75, 30, 64, 89, 77, 83, 47, 76, 42, 94, 72, 35, 31, 3, 89, 35, 98, 15, 74, 12, 99, 17, 68, 74, 79, 11, 80, 16, 75, 71, 11, 5, 85, 51, 35, 26, 38, 55, 64, 80, 81, 25, 37, 76, 64, 69, 21, 33, 4, 34, 96, 53, 18, 79, 2, 33, 68, 33, 71, 81, 76, 48, 26, 32, 55, 92, 51, 37, 11, 31, 28, 84, 13, 2, 61, 56, 86, 88, 67, 90, 88, 12, 28, 55, 56, 11, 61, 63, 28, 19, 76, 37, 3, 49, 96, 19, 45, 9, 89, 19, 75, 33, 24, 31, 88, 65, 29, 39, 53, 30, 98, 3, 62, 75, 17, 74, 80, 3, 67, 62, 24, 43, 78, 22, 3, 44, 88, 64, 27, 85, 9, 94, 65, 45, 84, 21, 41, 20, 75, 9, 11, 20, 4, 59, 31, 68, 99, 11, 51, 96, 56, 59, 94, 91, 97, 73, 43, 4, 17, 37, 92, 65, 77, 41, 14, 16, 14, 72, 97, 96, 67, 89, 69, 37, 81, 33, 18, 33, 53, 24, 12, 34, 67, 95, 77, 2, 4, 41, 51, 7, 14, 60, 15, 41, 53, 38, 24, 88, 59, 71, 99, 78, 59, 62, 25, 40, 42, 32, 47, 28, 41, 78, 29, 88, 78, 26, 77, 87, 64, 97, 20, 57, 33, 32, 46, 61, 3, 97, 64, 40, 7, 86, 75, 9, 80, 9, 4, 46, 34, 76, 43, 3, 65, 72, 23, 30, 71, 44, 81, 29, 88, 54, 4, 49, 88, 35, 94, 59, 30, 29, 27, 56, 14, 95, 42, 99, 3, 70, 68, 32, 56, 27, 15, 21, 39, 58, 37, 21, 91, 23, 57, 49, 46, 72, 90, 65, 16, 27, 81, 46, 95, 32, 77, 39, 72, 11, 10, 60, 67, 12, 69, 71, 68, 2, 23, 80, 11, 34, 5, 5, 77, 81, 90, 70, 38, 86, 54, 74, 81, 60, 74, 43, 90, 4, 16, 53, 49, 61, 9, 69, 80, 71, 10, 3, 46, 27, 84, 83, 3, 58, 46, 76, 49, 5, 17, 16, 25, 77, 34, 7, 81, 38, 22, 36, 29, 71, 78, 18, 61, 3, 3, 18, 21, 96, 45, 51, 31, 33, 70, 92, 39, 60, 60, 97, 79, 72, 30, 15, 30, 34, 70, 52, 46, 47, 48, 67, 21, 44, 51, 95, 63, 11, 19, 25, 49, 42, 25, 83, 94, 30, 9, 7, 31, 89, 11, 22, 83, 46, 34, 84, 49, 22, 21, 19, 49, 16, 9, 53, 67, 94, 72, 61, 25, 70, 52, 80, 16, 76, 76, 85, 95, 57, 42, 7, 77, 80, 73, 5, 24, 80, 41, 76, 87, 23, 34, 70, 28, 94, 83, 99, 59, 40, 88, 42, 74, 5, 48, 15, 25, 81, 91, 40, 27, 33, 96, 84, 16, 86, 33, 49, 99, 10, 29, 3, 65, 40, 87, 75, 65, 83, 93, 19, 10, 85, 26, 30, 89, 94, 68, 62, 98, 86, 19, 96, 84, 92, 44, 24, 68, 69, 44, 44, 97, 93]
    obstacles_y = [69, 81, 65, 40, 47, 78, 45, 66, 92, 27, 46, 66, 35, 10, 78, 84, 63, 30, 67, 17, 95, 66, 36, 35, 75, 2, 99, 40, 17, 63, 85, 99, 2, 76, 50, 28, 27, 47, 29, 3, 39, 11, 68, 30, 65, 35, 36, 74, 40, 62, 62, 47, 54, 55, 56, 93, 55, 9, 34, 21, 83, 35, 6, 44, 79, 29, 47, 16, 4, 40, 19, 35, 52, 74, 10, 71, 34, 7, 34, 62, 8, 26, 7, 67, 70, 13, 90, 49, 51, 96, 27, 39, 79, 44, 55, 41, 89, 96, 35, 81, 17, 22, 50, 16, 33, 86, 79, 21, 45, 2, 50, 47, 52, 70, 76, 9, 69, 60, 12, 14, 22, 3, 95, 55, 82, 71, 98, 51, 75, 24, 14, 39, 3, 15, 84, 3, 84, 58, 56, 39, 66, 56, 25, 95, 41, 52, 56, 8, 98, 17, 40, 35, 58, 98, 22, 65, 73, 95, 51, 10, 51, 70, 69, 8, 45, 98, 22, 16, 33, 60, 46, 34, 9, 70, 57, 57, 72, 27, 80, 77, 3, 10, 33, 27, 59, 66, 77, 48, 90, 66, 38, 37, 8, 79, 56, 53, 47, 93, 16, 65, 78, 99, 79, 97, 51, 8, 58, 84, 11, 45, 81, 52, 26, 85, 51, 54, 75, 40, 34, 93, 2, 66, 97, 82, 46, 14, 13, 89, 71, 76, 17, 31, 53, 30, 21, 24, 31, 45, 96, 43, 98, 82, 87, 97, 99, 38, 84, 24, 85, 44, 4, 27, 76, 31, 98, 61, 50, 97, 86, 66, 27, 34, 39, 42, 73, 70, 71, 37, 28, 59, 42, 62, 93, 64, 95, 47, 40, 81, 54, 77, 17, 45, 78, 22, 21, 40, 68, 55, 53, 89, 95, 20, 52, 17, 76, 26, 2, 62, 75, 74, 75, 31, 32, 93, 37, 12, 98, 87, 99, 79, 46, 18, 87, 91, 32, 99, 69, 77, 45, 41, 62, 26, 57, 52, 59, 53, 42, 87, 5, 61, 92, 28, 61, 91, 3, 61, 5, 6, 9, 56, 82, 3, 90, 13, 82, 95, 48, 99, 25, 77, 41, 27, 62, 17, 21, 23, 42, 23, 37, 66, 34, 47, 80, 44, 63, 95, 12, 87, 8, 98, 37, 91, 62, 16, 84, 24, 42, 2, 96, 36, 86, 85, 27, 92, 18, 65, 21, 6, 45, 36, 12, 45, 95, 11, 86, 40, 38, 4, 90, 9, 14, 67, 31, 50, 4, 41, 52, 71, 70, 62, 26, 30, 2, 66, 25, 45, 15, 43, 67, 92, 38, 56, 59, 79, 96, 90, 29, 47, 45, 25, 62, 67, 75, 81, 8, 47, 12, 9, 15, 23, 90, 59, 97, 79, 38, 28, 99, 67, 22, 12, 46, 29, 51, 65, 59, 13, 67, 87, 57, 17, 93, 38, 35, 62, 48, 17, 90, 30, 50, 13, 41, 63, 37, 22, 53, 28, 65, 66, 59, 86, 13, 59, 14, 95, 42, 95, 82, 41, 56, 12, 6, 9, 32, 68, 26, 7, 86, 76, 34, 18, 54, 32, 50, 25, 75, 89, 52, 47, 42, 95, 21, 79, 81, 18, 44, 80, 3, 70, 54, 60, 60, 3, 89, 92, 20, 66, 72, 40, 8, 77, 49, 61, 70, 23, 29, 2, 34, 32, 19, 92, 7, 15, 34, 97, 32, 74, 63, 94, 59, 24, 69, 85, 55, 71, 36, 54, 10, 79, 56, 43, 5, 25, 31, 15, 11, 15, 73, 18, 3, 83, 36, 75, 24, 11, 63, 27, 76, 31, 13, 58, 2, 40, 66, 16, 9, 58, 81, 4, 78, 79, 21, 58, 71, 95, 90, 39, 87, 8, 65, 64, 84, 48, 68, 77, 32, 17, 69, 43, 7, 93, 17, 20, 33, 49, 77, 26, 81, 7, 55, 2, 85, 32, 99, 26, 35, 57, 96, 76, 96, 64, 30, 19, 88, 82, 8, 29, 9, 16, 95, 67, 84, 62, 36, 31, 33, 40, 18, 25, 41, 78, 66, 20, 9, 86, 51, 36, 49, 2, 73, 78, 11, 26, 28, 66, 6, 34, 67, 65, 99, 88, 51, 64, 94, 87, 13, 40, 33, 44, 99, 55, 75, 79, 98, 58, 55, 20, 60, 44, 9, 53, 73, 33, 71, 94, 43, 36, 8, 14, 64, 90, 15, 85, 47, 93, 86, 80, 57, 71, 37, 48, 63, 68, 67, 35, 37, 18, 72, 14, 63, 65, 26, 9, 65, 43, 87, 87, 79, 35, 23, 82, 25, 80, 45, 9, 89, 28, 90, 50, 92, 21, 38, 45, 95, 42, 32, 93, 26, 51, 48, 72, 6, 99, 7, 82, 42, 58, 89, 3, 34, 54, 68, 13, 99, 81, 58, 84, 25, 85, 30, 93, 85, 6, 11, 61, 92, 32, 24, 86, 9, 17, 6, 12, 76, 57, 53, 61, 45, 26, 23, 46, 75, 26, 81, 67, 67, 68, 63, 99, 83, 15, 68, 45, 2, 4, 13, 63, 59, 80, 25, 7, 82, 78, 46, 85, 24, 60, 89, 64, 73, 88, 69, 97, 32, 92, 16, 67, 31, 21, 71, 41, 28, 98, 89, 68, 10, 81, 72, 13, 26, 94, 11, 65, 54, 5, 58, 84, 65, 44, 4, 10, 62, 69, 74, 15, 90, 86, 58, 82, 80, 87, 62, 34, 7, 66, 13, 42, 65, 83, 24, 63, 52, 90, 82, 48, 30, 22, 57, 49, 42, 44, 99, 95, 50, 61, 4, 51, 8, 42, 23, 44, 92, 62, 73, 57, 71, 59, 38, 61, 58, 43, 62, 79, 65, 62, 41, 57, 15, 26, 54, 3, 59, 27, 43, 48, 82, 41, 37, 46, 46, 95, 41, 64, 46, 29, 98, 20, 51, 36, 56, 9, 12, 2, 98, 4, 3, 61, 17, 94, 9, 98, 42, 98, 42, 43, 98, 79, 28, 90]

    for i in range(1, 100):
        ox.append(i)
        oy.append(1.0)
    for i in range(1, 100):
        ox.append(100.0)
        oy.append(i)
    for i in range(1, 101):
        ox.append(i)
        oy.append(100.0)
    for i in range(1, 101):
        ox.append(1.0)
        oy.append(i)
    plt.plot(ox, oy, "ks")
    for i in range(len(obstacles_x)):
        ox.append(obstacles_x[i])
        oy.append(obstacles_y[i])
        plt.plot(obstacles_x[i], obstacles_y[i], ".k")

    if show_animation:
        fig_manager = plt.get_current_fig_manager()
        fig_manager.full_screen_toggle()
        plt.title('PRM\nTest I - Start (5,5) > Goal (87,89)')
        plt.plot(sx, sy, "og")
        plt.plot(gx, gy, "xb")
        plt.axis("equal")

    rx, ry, dist, elapsed_time = prm_planning(sx, sy, gx, gy, ox, oy, robot_size)
    d = results(path(rx, ry))
    print("Total distance : ", d)    
    print("Total time : ", elapsed_time)
    print(rx)
    print(ry)

    # assert rx, 'Cannot found path'

    if show_animation:
        plt.plot(rx, ry, "-r")
        plt.pause(0.001)
        plt.show()

    return d, elapsed_time


if __name__ == '__main__':
    
    dist = []
    times = []

    for i in range(10):
        d,t = main()
        dist.append(d)
        times.append(t)

    print("Distances : ", dist)
    print("Average Distance : ", sum(dist)/len(dist))
    print("Execution Time : ", times)
    print("Average Execution Time : ", sum(times)/len(times))
