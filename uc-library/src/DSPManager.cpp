#include "presonus/dsp/DSPManager.hpp"
#include "presonus/dsp/RuntimeGlobals.hpp"

std::uint32_t DSPManager::getDSPStatus() { return getDSPState(); }
