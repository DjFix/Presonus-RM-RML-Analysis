#include "presonus/surface/LCDPort.hpp"
namespace Presonus::Surface {
LCDPort::LCDPort() : buffer(nullptr, 0, true), scribble() {}
LCDPort::~LCDPort() =
    default; // Genuine Buffer cleanup and actual embedded app lifetime.
bool LCDPort::isDisplayBufferActive(const void *) { return false; }
} // namespace Presonus::Surface
