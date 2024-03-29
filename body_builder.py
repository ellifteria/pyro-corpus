from __future__ import annotations
import pyrosim_z as psz
from typing import NamedTuple
from body_parts import *
import random
import numpy as np

def build_neurons(joint_names: list[str], sensor_parts: list[str]):
    sensor_neurons = []
    motor_neurons = []

    for part_id in sensor_parts:
        sensor_neuron_name = "SNx" + str(part_id) + "x"
        psz.Send_Sensor_Neuron(name=sensor_neuron_name, linkName=str(part_id))
        sensor_neurons.append(sensor_neuron_name)

    for joint_name in joint_names:
        motor_neuron_name = "MNx" + joint_name + "x"
        psz.Send_Motor_Neuron(name=motor_neuron_name, jointName=joint_name)
        motor_neurons.append(motor_neuron_name)

    return sensor_neurons, motor_neurons

def build_synapses(weights: NeuronWeightMatrix):
    sensor_neurons: list[str]   = list(weights.get_sensors().keys())
    motor_neurons: list[str]    = list(weights.get_motors().keys())
    for sensor_neuron in sensor_neurons:
        for motor_neuron in motor_neurons:
            psz.Send_Synapse(
                sourceNeuronName=sensor_neuron,
                targetNeuronName=motor_neuron,
                weight=weights.get(sensor_neuron, motor_neuron)
            )

def build_brain(joint_names, sensor_parts):
    sensor_neurons, motor_neurons = build_neurons(joint_names, sensor_parts)

    weight_matrix = NeuronWeightMatrix(sensor_neurons, motor_neurons, None)

    build_synapses(weight_matrix)

    return weight_matrix

def build_body(body_plan: BodyCons):
    abstract_centers        = []
    joint_names             = []
    sensor_parts            = []

    def build_body_recursively(body_plan: BodyCons, upstream_position: Position, upstream_cube_element: CubeElement, parrent_part_id: int, parent_center: Union[Position, None]=None, parent_size: Union[Dimensions, None]=None, parent_abstract_position: Union[Position, None]=None):
        body_cons_id                                    = body_plan.body_cons_id
        body_part: BodyPart                             = body_plan.body_part
        build_specifications: list[BuildSpecifications] = body_plan.build_specifications
        next_body_plans                                 = body_plan.next_body_plans

        current_specification: BuildSpecifications = build_specifications[0]

        direction_to_build = current_specification.direction_to_build
        repetitions = current_specification.repitions
        axis = current_specification.axis

        specific_body_cons_id = "{}r{}".format(body_cons_id, repetitions)
        current_part_id = specific_body_cons_id

        if body_part.get_properties()['brain'] == True:
            current_part_id = current_part_id + 'B'

        if parrent_part_id == -1:
            my_abstract_position = Position(0, 0, 0)
        else:
            joint_name: str = create_joint(
                upstream_center=parent_center,
                parent_part_size=parent_size,
                joint_attachment_element=direction_to_build,
                joint_type=body_part.properties['joint'],
                axis=axis,
                parent_part_id=parrent_part_id,
                current_part_id=current_part_id)
            my_abstract_position = Position(*add_xyz(parent_abstract_position, direction_to_build.value))
            joint_names.append(joint_name)

        my_center, my_size = body_part.create_body_part(
            upstream_position=upstream_position,
            attachment_point_on_child=direction_to_build,
            piece_id=current_part_id)
        
        if body_part.get_properties()['sensor'] == True or body_part.get_properties()['brain'] == True:
            sensor_parts.append(current_part_id)
        
        if my_abstract_position in abstract_centers:
            raise ValueError("Center already in design, cannot build")
        abstract_centers.append(my_abstract_position)
        
        repetitions_left = repetitions - 1

        if repetitions_left <= 0 and next_body_plans is None:
            return

        if repetitions_left <= 0:
            next_parent_id = current_part_id
            for direction in next_body_plans:
                next_body_plan = next_body_plans[direction]
                build_body_recursively(body_plan=next_body_plan,
                                                            upstream_position=(0, 0, 0),
                                                            upstream_cube_element=direction,
                                                            parrent_part_id=next_parent_id,
                                                            parent_center=my_center,
                                                            parent_size=my_size,
                                                            parent_abstract_position=my_abstract_position)
            return
        
        new_build_specifications = [BuildSpecifications(direction_to_build=direction_to_build, repitions=repetitions_left, axis=axis)]
        
        next_body_plan = BodyCons(body_cons_id=body_cons_id,
                                  body_part=body_part,
                                  build_specifications=new_build_specifications,
                                  next_body_plans=next_body_plans)
        return  build_body_recursively(body_plan=next_body_plan,
                                      upstream_position=(0, 0, 0),
                                      upstream_cube_element=direction_to_build,
                                      parrent_part_id=current_part_id,
                                      parent_center=my_center,
                                      parent_size=my_size,
                                      parent_abstract_position=my_abstract_position)
    
    build_body_recursively(body_plan=body_plan,
                           upstream_position=Position(0, 0, 2),
                           upstream_cube_element=CubeElement.CENTER,
                           parrent_part_id=-1)
    
    return joint_names, sensor_parts, abstract_centers


if __name__ == '__main__':
    body_plan = BodyCons(0, FixedSizeBodyPiece(), [BuildSpecifications(CubeElement.FRONT, 3, Axes.X)],
                        {CubeElement.TOP: BodyCons(1, FixedSizeSensorPiece(), [BuildSpecifications(CubeElement.TOP, 3, Axes.Z)],
                                                    {CubeElement.BACK: BodyCons(2, FixedSizeUnmovableBodyPiece(), [BuildSpecifications(CubeElement.BACK, 5, Axes.X)],None),
                                                    CubeElement.RIGHT: BodyCons(3, FixedSizeUnmovableSensorPiece(), [BuildSpecifications(CubeElement.RIGHT, 2, Axes.Y)], None)}),
                        CubeElement.RIGHT: BodyCons(4, FixedSizeUnmovableSensorPiece(), [BuildSpecifications(CubeElement.RIGHT, 2, Axes.Y)], None),
                        CubeElement.LEFT: BodyCons(5, FixedSizeSensorPiece(), [BuildSpecifications(CubeElement.LEFT, 2, Axes.Y)], 
                                                    {CubeElement.TOP:BodyCons(6, FixedSizeUnmovableBodyPiece(), [BuildSpecifications(CubeElement.TOP, 3, Axes.Z)],None)}),
                        CubeElement.FRONT: BodyCons(7, FixedSizeSensorPiece(), [BuildSpecifications(CubeElement.FRONT, 2, Axes.X)], None),
                        })

    solution_id = 0

    psz.Start_URDF("./data/robot/body{}.urdf".format(solution_id))

    joint_names, sensor_parts, abstract_centers = build_body(body_plan)

    psz.end()

    print(joint_names)
    print(sensor_parts)
    print(abstract_centers)

    psz.Start_NeuralNetwork("./data/robot/brain{}.nndf".format(solution_id))

    weight_matrix = build_brain(joint_names, sensor_parts)

    psz.end()