import math

from OCP.gp import (
    gp_Pnt,
    gp,
    gp_Vec,
    gp_Trsf,
    gp_Ax2,
    gp_Ax3,
    gp_Pnt2d,
    gp_Dir2d,
    gp_Ax2d,
    gp_Pln,
)
from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCP.GCE2d import GCE2d_MakeSegment
from OCP.Geom import Geom_CylindricalSurface
from OCP.Geom2d import Geom2d_Ellipse, Geom2d_TrimmedCurve
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_Transform,
)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepOffsetAPI import (
    BRepOffsetAPI_MakeThickSolid,
    BRepOffsetAPI_ThruSections,
)
from OCP.BRepLib import BRepLib
from OCP.BRep import BRep_Builder
from OCP.GeomAbs import GeomAbs_Plane
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.TopoDS import TopoDS, TopoDS_Compound, TopoDS_Face
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopTools import TopTools_ListOfShape
from volmdlr.composite_shapes import Compound


def face_is_plane(face: TopoDS_Face) -> bool:
    """
    Returns True if the TopoDS_Face is a plane, False otherwise
    """
    surf = BRepAdaptor_Surface(face, True)
    surf_type = surf.GetType()
    return surf_type == GeomAbs_Plane


def geom_plane_from_face(aFace: TopoDS_Face) -> gp_Pln:
    """
    Returns the geometric plane entity from a planar surface
    """
    return BRepAdaptor_Surface(aFace, True).Plane()


height = 0.7
width = 0.5
thickness = 0.3

print("creating bottle")
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

# The face that we'll sweep to make the prism
myFaceProfile = BRepBuilderAPI_MakeFace(myWireProfile)

# We want to sweep the face along the Z axis to the height
aPrismVec = gp_Vec(0, 0, height)
myBody_step1 = BRepPrimAPI_MakePrism(myFaceProfile.Face(), aPrismVec)

# Add fillets to all edges through the explorer
mkFillet = BRepFilletAPI_MakeFillet(myBody_step1.Shape())
anEdgeExplorer = TopExp_Explorer(myBody_step1.Shape(), TopAbs_EDGE)

while anEdgeExplorer.More():
    anEdge = TopoDS.Edge_s(anEdgeExplorer.Current())
    mkFillet.Add(thickness / 12.0, anEdge)

    anEdgeExplorer.Next()

# Create the neck of the bottle
neckLocation = gp_Pnt(0, 0, height)
neckAxis = gp.DZ_s()
neckAx2 = gp_Ax2(neckLocation, neckAxis)

myNeckRadius = thickness / 4.0
myNeckHeight = height / 10.0

mkCylinder = BRepPrimAPI_MakeCylinder(neckAx2, myNeckRadius, myNeckHeight)

myBody_step2 = BRepAlgoAPI_Fuse(mkFillet.Shape(), mkCylinder.Shape())

# Our goal is to find the highest Z face and remove it
zMax = -1.0

# We have to work our way through all the faces to find the highest Z face so we can remove it for the shell
aFaceExplorer = TopExp_Explorer(myBody_step2.Shape(), TopAbs_FACE)
while aFaceExplorer.More():
    aFace = TopoDS.Face_s(aFaceExplorer.Current())
    if face_is_plane(aFace):
        aPlane = geom_plane_from_face(aFace)

        # We want the highest Z face, so compare this to the previous faces
        aPntLoc = aPlane.Location()
        aZ = aPntLoc.Z()
        if aZ > zMax:
            zMax = aZ
    aFaceExplorer.Next()

facesToRemove = TopTools_ListOfShape()
facesToRemove.Append(aFace)

mk_thick_solid = BRepOffsetAPI_MakeThickSolid()
mk_thick_solid.MakeThickSolidByJoin(
    myBody_step2.Shape(), facesToRemove, -thickness / 50.0, 0.001
)
mk_thick_solid.Build()
myBody_step3 = mk_thick_solid.Shape()

# Set up our surfaces for the threading on the neck
neckAx2_Ax3 = gp_Ax3(neckLocation, gp.DZ_s())
aCyl1 = Geom_CylindricalSurface(neckAx2_Ax3, myNeckRadius * 0.99)
aCyl2 = Geom_CylindricalSurface(neckAx2_Ax3, myNeckRadius * 1.05)

# Set up the curves for the threads on the bottle's neck
aPnt = gp_Pnt2d(2.0 * math.pi, myNeckHeight / 2.0)
aDir = gp_Dir2d(2.0 * math.pi, myNeckHeight / 4.0)
anAx2d = gp_Ax2d(aPnt, aDir)

aMajor = 2.0 * math.pi
aMinor = myNeckHeight / 10.0

anEllipse1 = Geom2d_Ellipse(anAx2d, aMajor, aMinor)
anEllipse2 = Geom2d_Ellipse(anAx2d, aMajor, aMinor / 4.0)

anArc1 = Geom2d_TrimmedCurve(anEllipse1, 0, math.pi)
anArc2 = Geom2d_TrimmedCurve(anEllipse2, 0, math.pi)

anEllipsePnt1 = anEllipse1.Value(0)
anEllipsePnt2 = anEllipse1.Value(math.pi)

aSegment = GCE2d_MakeSegment(anEllipsePnt1, anEllipsePnt2)

# Build edges and wires for threading
anEdge1OnSurf1 = BRepBuilderAPI_MakeEdge(anArc1, aCyl1)
anEdge2OnSurf1 = BRepBuilderAPI_MakeEdge(aSegment.Value(), aCyl1)
anEdge1OnSurf2 = BRepBuilderAPI_MakeEdge(anArc2, aCyl2)
anEdge2OnSurf2 = BRepBuilderAPI_MakeEdge(aSegment.Value(), aCyl2)

threadingWire1 = BRepBuilderAPI_MakeWire(anEdge1OnSurf1.Edge(), anEdge2OnSurf1.Edge())
threadingWire2 = BRepBuilderAPI_MakeWire(anEdge1OnSurf2.Edge(), anEdge2OnSurf2.Edge())

# Compute the 3D representations of the edges/wires
BRepLib.BuildCurves3d_s(threadingWire1.Shape())
BRepLib.BuildCurves3d_s(threadingWire2.Shape())

# Create the surfaces of the threading
aTool = BRepOffsetAPI_ThruSections(True)
aTool.AddWire(threadingWire1.Wire())
aTool.AddWire(threadingWire2.Wire())
aTool.CheckCompatibility(False)
myThreading = aTool.Shape()

# Build the resulting compound
bottle = TopoDS_Compound()
aBuilder = BRep_Builder()
aBuilder.MakeCompound(bottle)
aBuilder.Add(bottle, myBody_step3)
aBuilder.Add(bottle, myThreading)
print("bottle finished")

if __name__ == "__main__":

    model = Compound.from_ocp(bottle)
    model.babylonjs()