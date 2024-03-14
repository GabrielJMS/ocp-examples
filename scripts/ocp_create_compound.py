from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp, gp_Pnt, gp_Ax2, gp_Vec, gp_Quaternion, gp_Trsf
from OCP.TopoDS import TopoDS_Shape, TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.TopLoc import TopLoc_Location
import math
from volmdlr.composite_shapes import Compound


def create_cylinder(diameter: float, length: float) -> TopoDS_Shape:
    """
    Creates a cylinder from a diameter and a width.

    :param diameter: The overall diameter of a of the cylinder.
    :param length: the cylinder length.
    :return: TopoDS_Shape
    """
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0.0, -length / 2, 0.0), gp.DY_s()), diameter / 2, length).Shape()


WHEEL_DIAMETER = 5
WHEEL_WIDTH = WHEEL_DIAMETER / 6
AXLE_DIAMETER = WHEEL_DIAMETER / 5
AXLE_LENGTH = WHEEL_DIAMETER * 2.5
WHEEL_BASE = WHEEL_DIAMETER * 3.5

wheel = create_cylinder(WHEEL_DIAMETER, WHEEL_WIDTH)

axle = create_cylinder(AXLE_DIAMETER, AXLE_LENGTH)

# Create a wheel-axle-wheel assembly
wheel_axle = TopoDS_Compound()
bbuilder = BRep_Builder()
bbuilder.MakeCompound(wheel_axle)

wright_trsf = gp_Trsf()
wright_trsf.SetTranslationPart(gp_Vec(0.0, AXLE_LENGTH / 2, 0))
wright_location = TopLoc_Location(wright_trsf)

qn = gp_Quaternion(gp_Vec(0.0, 0.0, 1.0), math.pi)
wleft_tr = gp_Trsf()
wleft_tr.SetRotation(qn)

wleft_trsf = gp_Trsf()
wleft_trsf.Multiply(wright_trsf.Inverted())
wleft_trsf.Multiply(wleft_tr)
wleft_location = TopLoc_Location(wleft_trsf)

bbuilder.Add(wheel_axle, wheel.Moved(wleft_location))
bbuilder.Add(wheel_axle, wheel.Moved(wright_location))
bbuilder.Add(wheel_axle, axle)  # Without transformation.

# create chassis assembly
chassis = TopoDS_Compound()
bbuilder = BRep_Builder()
bbuilder.MakeCompound(chassis)

wfront_T = gp_Trsf()
wfront_T.SetTranslationPart(gp_Vec(WHEEL_BASE / 2, 0, 0))

wrear_T = gp_Trsf()
wrear_T.SetTranslationPart(gp_Vec(-WHEEL_BASE / 2, 0, 0))

wfront_location = TopLoc_Location(wfront_T)
wrear_location = TopLoc_Location(wrear_T)

bbuilder.Add(chassis, wheel_axle.Moved(wfront_location))
bbuilder.Add(chassis, wheel_axle.Moved(wrear_location))

model = Compound.from_ocp(chassis)
model.babylonjs()
