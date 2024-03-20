from OCP.BRep import BRep_Tool
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.TopoDS import TopoDS, TopoDS_Compound, TopoDS_Face
from OCP.gp import (
    gp_Pnt,
    gp,
    gp_Trsf,
)
from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_Transform,
)

height = 0.7
width = 0.5
thickness = 0.3


# The points we'll use to create the profile of the bottle's body
aPnt1 = gp_Pnt(-width / 2.0, 0, 0)
aPnt2 = gp_Pnt(-width / 2.0, -thickness / 4.0, 0)
aPnt3 = gp_Pnt(0, -thickness / 2.0, 0)
aPnt4 = gp_Pnt(width / 2.0, -thickness / 4.0, 0)
aPnt5 = gp_Pnt(width / 2.0, 0, 0)

aArcOfCircle = GC_MakeArcOfCircle(aPnt2, aPnt3, aPnt4)
aSegment1 = GC_MakeSegment(aPnt1, aPnt2)
aSegment2 = GC_MakeSegment(aPnt4, aPnt5)

# Could also construct the line edges directly using the points instead of the resulting line
aEdge1 = BRepBuilderAPI_MakeEdge(aSegment1.Value())
aEdge2 = BRepBuilderAPI_MakeEdge(aArcOfCircle.Value())
aEdge3 = BRepBuilderAPI_MakeEdge(aSegment2.Value())

# Create a wire out of the edges
aWire = BRepBuilderAPI_MakeWire(aEdge1.Edge(), aEdge2.Edge(), aEdge3.Edge())

# Quick way to specify the X axis
xAxis = gp.OX_s()
# Set up the mirror
aTrsf = gp_Trsf()
aTrsf.SetMirror(xAxis)

# Apply the mirror transformation
aBRespTrsf = BRepBuilderAPI_Transform(aWire.Wire(), aTrsf)

# Get the mirrored shape back out of the transformation and convert back to a wire
aMirroredShape = aBRespTrsf.Shape()

# A wire instead of a generic shape now
aMirroredWire = TopoDS.Wire_s(aMirroredShape)

# Combine the two constituent wires
mkWire = BRepBuilderAPI_MakeWire()
mkWire.Add(aWire.Wire())
mkWire.Add(aMirroredWire)
myWireProfile = mkWire.Wire()

# How to verify if a wire is closed (loop, contour)?
print(f"Is this wire closed: {BRep_Tool.IsClosed_s(myWireProfile)}") # returns True if it has no free ends
print(f"Is this wire closed: {BRep_Tool.IsClosed_s(aWire.Wire())}")


def iter_edges_from_wire(wire):
    """
    Generator / Iterator over the edges of a wire.

    It preserves the order of the edges.
    """
    # The WireExplorer is a tool to explore the edges of a wire in a connection order
    exp = BRepTools_WireExplorer(wire)
    while exp.More():
        yield exp.Current()
        exp.Next()
