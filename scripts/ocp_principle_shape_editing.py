"""
In Open CASCADE, modifying a shape in place is not supported. This implies that whenever we intend to modify a subshape
of a parent shape (such as a face within a shell), the entire data structure must be reconstructed from the top down.
For instance, if we modify a face within a shell, a new shell is generated to substitute the old one.
Similarly, if this shell is part of a solid, a new solid is created as well. Open CASCADE facilitates such
modifications through the BRepTools_ReShape class within the BRepTools package. This class enables the seamless
execution of such transformations on BRep shapes, ensuring the integrity and coherence of the geometric model
throughout the process.
"""
from OCP.BRep import BRep_Tool, BRep_Builder
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCP.BRepTools import BRepTools_ReShape, BRepTools
from OCP.Geom import Geom_Circle
from OCP.TopExp import TopExp_Explorer, TopExp
from OCP.TopoDS import TopoDS, TopoDS_Wire, TopoDS_Edge, TopoDS_Face, TopoDS_Shape, TopoDS_Iterator
from OCP.TopAbs import (TopAbs_FACE, TopAbs_WIRE)
from OCP.TopTools import TopTools_IndexedMapOfShape
from volmdlr.core import VolumeModel
import os

data_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def is_circular(wire):
    explorer = TopoDS_Iterator(wire)
    _edge = TopoDS.Edge_s(explorer.Value())
    u_start, u_end = BRep_Tool().Range_s(_edge)
    curve = BRep_Tool().Curve_s(_edge, u_start, u_end)
    if curve.IsKind("Geom_Circle"):
        return True, curve.Circ()
    elif curve.IsInstance("Geom_TrimmedCurve"):
        if curve.BasisCurve.IsKind("Geom_Circle"):
            return True, curve.Circ()
    return False, None


# Reads the data from a .brep file
shape = TopoDS_Shape()
builder = BRep_Builder()
BRepTools.Read_s(shape, os.path.join(data_folder, "compound_of_faces.brep"), builder)

# initialize the shape editor
shape_editor = BRepTools_ReShape()

# search in a Compound all the faces that have a circular hole, if any is found, then we divise its radius by 2.
# sets a face's explorer
exp = TopExp_Explorer(shape, TopAbs_FACE)
while exp.More():
    face = TopoDS.Face_s(exp.Current())

    all_wires = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(face, TopAbs_WIRE, all_wires)
    # if the face has only one wire, this means that it doesn't contain holes (inner wires), so we go to the next face.
    if all_wires.Extent() == 1:
        exp.Next()
        continue

    # gets the inner wire
    inner_wire = None
    outer_wire = BRepTools.OuterWire_s(face)
    for w in range(1, all_wires.Extent() + 1):
        # IsPartner -> returns True if two shapes are partners, i.e. if they share the same TShape.
        # Locations and Orientations may differ.
        if all_wires.FindKey(w).IsPartner(outer_wire):
            continue
        inner_wire = TopoDS.Wire_s(all_wires.FindKey(w))
    if inner_wire is None:
        exp.Next()
        continue

    is_circle, circ_props = is_circular(inner_wire)
    if is_circle:
        circ_props.SetRadius(circ_props.Radius() / 2.)
        circle = Geom_Circle(circ_props)
        edge = BRepBuilderAPI_MakeEdge(circle).Edge()
        wire = BRepBuilderAPI_MakeWire(edge)
        # we set the modification wanted.
        shape_editor.Replace(inner_wire, wire.Wire())
    exp.Next()

# This will return a new Compound with the specified modification on the inner wire. Note that we didn't need to
# specify any information about the data structure. We only need to predefine the modification wanted and the
# BRepTools_ReShape will detect that the wire belongs to a face and that this face is part of a Compound and will
# return at the end a new Compound.
new_shape = shape_editor.Apply(shape)
model1 = VolumeModel.from_ocp([TopoDS.Compound_s(shape)])
model2 = VolumeModel.from_ocp([TopoDS.Compound_s(new_shape)])

model1.babylonjs()
model2.babylonjs()
