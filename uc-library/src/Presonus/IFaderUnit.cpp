#include "presonus/IFaderUnit.hpp"
namespace Presonus {
// Native D0 resets the vptr then invokes unsized global delete. The C++ virtual
// destructor emits that lifecycle; this portable partial class asserts no ABI.
IFaderUnit::~IFaderUnit() = default;
} // namespace Presonus
