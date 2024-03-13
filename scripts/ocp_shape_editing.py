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


# search in a Compound all the faces that have a circular hole, if any is found, then we divise its radius by 2.
shape = TopoDS_Shape()
builder = BRep_Builder()
BRepTools.Read_s(shape, os.path.join(data_folder, "compound_of_faces.brep"), builder)

shape_editor = BRepTools_ReShape()

exp = TopExp_Explorer(shape, TopAbs_FACE)
while exp.More():
    face = TopoDS.Face_s(exp.Current())

    all_wires = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(face, TopAbs_WIRE, all_wires)
    if all_wires.Extent() == 1:
        exp.Next()
        continue

    inner_wire = None
    outer_wire = BRepTools.OuterWire_s(face)

    for w in range(1, all_wires.Extent() + 1):
        if all_wires.FindKey(w).IsPartner(outer_wire):
            continue
        inner_wire = TopoDS.Wire_s(all_wires.FindKey(w))
    if inner_wire is None:
        continue

    is_circle, circ_props = is_circular(inner_wire)
    if is_circle:
        circ_props.SetRadius(circ_props.Radius() / 2.)
        circle = Geom_Circle(circ_props)
        edge = BRepBuilderAPI_MakeEdge(circle).Edge()
        wire = BRepBuilderAPI_MakeWire(edge)
        shape_editor.Replace(inner_wire, wire.Wire())
    exp.Next()
new_shape = shape_editor.Apply(shape)
model1 = VolumeModel.from_ocp([TopoDS.Compound_s(shape)])
model2 = VolumeModel.from_ocp([TopoDS.Compound_s(new_shape)])

model1.babylonjs()
model2.babylonjs()
