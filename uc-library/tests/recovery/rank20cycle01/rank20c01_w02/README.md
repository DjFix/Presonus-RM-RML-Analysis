# Bounded source-port replay

MackieControlUnit D1 is a partial source port onto the pinned CCL 5.0.0
Component lifecycle. The actual provider destructor is executed directly for
independent observations and the port is checked against those observations.
The native prefix fixture executes exact original ARM instructions and stops
before calling Core; no Core binary implementation is decoded or executed.
Original interface-table values, extra bases, object layout and ARM ABI are not
asserted. Compiler-generated D0/D2 are not admitted as original recovered targets.

Run checks.py format, checks.py compile, check_symbols.py on scratch/port.o, then
replay.py scratch/driver fixtures.json. All paths are repository relative in the
handoff. Root owns production partition and canonical CTest integration. Do not
admit this local proof as original full lifecycle verification.

MeterControl::isHorizontal retains the existing MeterControl declaration/state
and calls the existing portableIsVertical helper. Native isHorizontal and its
expanded isVertical body execute for 136 rectangles, with only the external
Core View::getSize call adapted to an immutable supplied rectangle value. No
Core implementation instruction executes. The domain excludes signed overflow;
original bool return declaration and class layout remain unresolved.
