#include "presonus/MackieControlUnit.hpp"
namespace Presonus {
// Compiler-generated table transitions plus real CCL Component cleanup replace
// the original four ARM interface-table stores and Component D2 call. This is a
// deliberate source adaptation; original extra interfaces/ABI remain
// unresolved.
MackieControlUnit::~MackieControlUnit() = default;
} // namespace Presonus
