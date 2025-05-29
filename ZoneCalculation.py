import math
import numpy as np

def CalculateZone(Extendedobjects):

    golden_ratio = 1.618

    sigma_0 = 1.4
    f_vel_x = 0.2
    f_vel_y = 1
    A0 = 1
    t1 = 0.15
    t2 = 1
    default_safety_dist = 0.45
    robot_size = 0.2
    min_safety_dist = default_safety_dist + robot_size
    d_closest = 0
    d_max = 10
    v_robot_max = 1
    v_robot = 0

    for person in Extendedobjects.extendedObjectsList:
        if person.tracking_state.name == "TERMINATE": # Skip terminated people
            continue

        # Person velocity, distance and position calculation
        v = math.sqrt(person.velocity[0]**2+person.velocity[2]**2)
        distance = math.sqrt(person.position[0]**2+person.position[2]**2)
        xz_pos = [person.position[0],-person.position[2]]

        # Safety zone calculation
        if len(person.bounding_box) > 0:
            person_radius = math.sqrt((person.bounding_box[0][0]-person.position[0])**2+(person.bounding_box[0][2]-person.position[2])**2)
            if person_radius > default_safety_dist:
                min_safety_dist = person_radius + robot_size
        safety_zone = v*(t1+t2)+min_safety_dist
        safety_zone_x = v*f_vel_x*(t1+t2)+min_safety_dist
        safety_zone_y = v*f_vel_y*(t1+t2)+min_safety_dist
        person.safety_zone = safety_zone

        # Comfort zone calculation
        person.zone_a = [safety_zone_y * golden_ratio ** i for i in range(5)]
        person.zone_b = [safety_zone_x * golden_ratio ** i for i in range(5)]

        # Person movement direction calculation
        theta = math.degrees(math.atan2(person.velocity[2],person.velocity[0]))
        person.bodyMovementAngle = theta
        theta_gauss = math.radians(theta + 90)

        # Person movement direction involvement
        if abs(theta_gauss) < math.pi / 2:
            f_head = np.interp(abs(theta_gauss), [0, math.pi / 2], [f_vel_x, f_vel_y])
            sigma_y = sigma_0 + (v * f_vel_y * f_head)
            sigma_x = sigma_0 + (v * f_vel_x * 1)
        else:
            sigma_y = sigma_0 + (v * f_vel_y * 1)
            sigma_x = sigma_0 + (v * f_vel_x * 1)

        # 2D Gaussian function
        A = A0 + v
        term1 = (xz_pos[0]*np.cos(theta_gauss)+xz_pos[1]*np.sin(theta_gauss))**2/(2*sigma_x**2)
        term2 = (-xz_pos[0]*np.sin(theta_gauss)+xz_pos[1]*np.cos(theta_gauss))**2/(2*sigma_y**2)
        Z_2D_Gauss = A*np.exp(-(term1+term2))
        v_robot_calc = A - Z_2D_Gauss

        # Closest person calculation
        if v_robot_calc < v_robot_max:
            v_robot_max = v_robot_calc
            v_robot = v_robot_calc
        else:
            v_robot = v_robot_max
        if distance < d_max:
            d_max = distance
            d_closest = distance
            if d_closest <= safety_zone:
                v_robot = 0

    return v_robot, d_closest
