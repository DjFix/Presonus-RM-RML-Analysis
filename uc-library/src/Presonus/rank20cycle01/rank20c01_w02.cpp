#include "presonus/rank20cycle01/rank20c01_w02.hpp"
#include "presonus/MeterControl.hpp"

namespace Presonus {
bool MeterControl::isHorizontal() const { return !portableIsVertical(); }

// Compiler-generated table transitions plus real CCL Component cleanup replace
// the original four ARM interface-table stores and Component D2 call. This is a
// deliberate source adaptation; original extra interfaces/ABI remain
// unresolved.
MackieControlUnit::~MackieControlUnit() = default;
} // namespace Presonus
