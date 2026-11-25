#include "presonus/MixerClassManager.hpp"

namespace Presonus {

MixerClassManager::MixerClassManager() : classes_(0, 5) {}

MixerClassManager::~MixerClassManager() {
  for (int index = 0; index < classes_.count(); ++index)
    delete classes_.at(index);
}

} // namespace Presonus
