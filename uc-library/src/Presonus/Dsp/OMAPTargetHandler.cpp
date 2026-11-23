#include "presonus/dsp/OMAPTargetHandler.hpp"
#include <new>
namespace Presonus::Dsp {
// Retain the original ELF weak binding on the canonical Linux target.
__attribute__((weak)) void OMAPTargetHandler::release() {
  ::operator delete(static_cast<void *>(this));
}
__attribute__((weak)) void OMAPTargetHandler::getProperty(Core::Property &) {}
} // namespace Presonus::Dsp
