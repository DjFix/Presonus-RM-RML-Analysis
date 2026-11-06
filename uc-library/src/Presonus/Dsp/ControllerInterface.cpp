#include "presonus/dsp/Controller.hpp"
namespace Presonus::Dsp {
// Each original 16-byte body only establishes/restores its stack frame.
// Do not query interfaces, inspect property payloads, or manufacture a return.
void Controller::getProperty(Core::Property &) {}
void Controller::processIdle() {}
} // namespace Presonus::Dsp
